package main

import (
	"bufio"
	"compress/gzip"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
)

// Result содержит результат обработки одной строки.
type Result struct {
	Success bool
	IsError bool
}

// ProcessLine обрабатывает одну строку TSV: парсит и загружает в Memcached.
func ProcessLine(line string, deviceMemc map[string]string, setter *MemcachedSetter) Result {
	line = strings.TrimSpace(line)
	if line == "" {
		return Result{Success: true, IsError: false}
	}

	ai := ParseAppsInstalled(line)
	if ai == nil {
		return Result{Success: false, IsError: true}
	}

	memcAddr := deviceMemc[ai.DevType]
	if memcAddr == "" {
		log.Printf("unknown device type: %s", ai.DevType)
		return Result{Success: false, IsError: true}
	}

	ok := setter.Set(ai.DevType, ai.DevID, ai.Apps, ai.Lat, ai.Lon)
	if setter.dryRun {
		log.Printf(
			"%s - %s:%s -> apps: %v lat: %.4f lon: %.4f",
			memcAddr, ai.DevType, ai.DevID, ai.Apps, ai.Lat, ai.Lon,
		)
	}

	return Result{Success: ok, IsError: !ok}
}

// ProcessFile обрабатывает один TSV.gz файл конкурентно.
// Файлы читаются последовательно, но строки обрабатываются параллельно.
func ProcessFile(path string, deviceMemc map[string]string, setter *MemcachedSetter, workers int) (processed, errors int) {
	f, err := os.Open(path)
	if err != nil {
		log.Printf("error opening file %s: %v", path, err)
		return 0, 0
	}
	defer f.Close()

	gzr, err := gzip.NewReader(f)
	if err != nil {
		log.Printf("error creating gzip reader for %s: %v", path, err)
		return 0, 0
	}
	defer gzr.Close()

	// Считываем все строки из файла.
	var lines []string
	scanner := bufio.NewScanner(gzr)
	// Увеличиваем размер буфера для длинных строк.
	buf := make([]byte, 0, 64*1024)
	scanner.Buffer(buf, 1024*1024)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		log.Printf("error reading file %s: %v", path, err)
		return 0, 0
	}

	if len(lines) == 0 {
		return 0, 0
	}

	// Обрабатываем строки конкурентно.
	var (
		processedN int64
		errorsN    int64
		sem        = make(chan struct{}, workers)
		wg         sync.WaitGroup
	)

	for _, line := range lines {
		sem <- struct{}{} // acquire
		wg.Add(1)
		go func(l string) {
			defer wg.Done()
			defer func() { <-sem }() // release

			res := ProcessLine(l, deviceMemc, setter)
			if res.IsError {
				atomic.AddInt64(&errorsN, 1)
			} else {
				atomic.AddInt64(&processedN, 1)
			}
		}(line)
	}

	wg.Wait()

	return int(processedN), int(errorsN)
}

// DotRename переименовывает файл, добавляя точку в начало имени.
// Используется для отметки обработанных файлов.
func DotRename(path string) error {
	dir := filepath.Dir(path)
	base := filepath.Base(path)
	newPath := filepath.Join(dir, "."+base)
	return os.Rename(path, newPath)
}

// NormalErrRate — допустимый уровень ошибок.
const NormalErrRate = 0.01

// CheckErrorRate проверяет уровень ошибок и логирует результат.
func CheckErrorRate(processed, errors int) {
	if processed == 0 {
		return
	}
	errRate := float64(errors) / float64(processed)
	if errRate < NormalErrRate {
		log.Printf("acceptable error rate (%.4f). successful load", errRate)
	} else {
		log.Printf("high error rate (%.4f > %.4f). failed load", errRate, NormalErrRate)
	}
}

// ProtoTest тестирует сериализацию/десериализацию данных.
func ProtoTest() {
	sample := []string{
		"idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23",
		"gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424",
	}

	for _, line := range sample {
		ai := ParseAppsInstalled(line)
		if ai == nil {
			panic(fmt.Sprintf("failed to parse: %s", line))
		}
		data := SerializeUserApps(ai.Apps, ai.Lat, ai.Lon)
		if len(data) == 0 {
			panic("serialization produced empty data")
		}
		log.Printf("proto test: %s:%s -> %d bytes", ai.DevType, ai.DevID, len(data))
	}
}
