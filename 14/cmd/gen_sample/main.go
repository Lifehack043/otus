// Генератор тестовых TSV.gz файлов со случайными данными устройств.
//
// Пример использования:
//
#   go run gen_sample.go .

package main

import (
	"compress/gzip"
	"crypto/md5"
	"flag"
	"fmt"
	"log"
	"math/rand"
	"os"
	"path/filepath"
	"strconv"
	"time"
)

// devIDTypes — поддерживаемые типы идентификаторов устройств.
var devIDTypes = []string{"idfa", "gaid", "adid", "dvid"}

const (
	maxDevID  = 100_000_000
	maxApps   = 100
	appsPool  = 10_000
	numFiles  = 3
	fileSize  = 0.5 * 1024 * 1024 * 1024 // ~512 MiB
)

func randomPoint() (float64, float64) {
	return rand.Float64()*360 - 180, rand.Float64()*180 - 90
}

func genLine(w *gzip.Writer) (int, error) {
	devType := devIDTypes[rand.Intn(len(devIDTypes))]
	devID := fmt.Sprintf("%x", md5.Sum([]byte(strconv.Itoa(rand.Intn(maxDevID)))))
	lat, lon := randomPoint()

	numApps := rand.Intn(maxApps) + 1
	seen := make(map[int]struct{}, numApps)

	// Формируем строку по частям для экономии памяти.
	var n int

	// devType\t
	b := []byte(devType + "\t")
	nn, err := w.Write(b)
	n += nn
	if err != nil {
		return n, err
	}

	// devID\t
	b = append([]byte(devID), '\t')
	nn, err = w.Write(b)
	n += nn
	if err != nil {
		return n, err
	}

	// lat\t
	b = []byte(strconv.FormatFloat(lat, 'f', -1, 64) + "\t")
	nn, err = w.Write(b)
	n += nn
	if err != nil {
		return n, err
	}

	// lon\t
	b = []byte(strconv.FormatFloat(lon, 'f', -1, 64) + "\t")
	nn, err = w.Write(b)
	n += nn
	if err != nil {
		return n, err
	}

	// apps
	first := true
	for len(seen) < numApps {
		id := rand.Intn(appsPool)
		if _, ok := seen[id]; ok {
			continue
		}
		seen[id] = struct{}{}
		if !first {
			nn, err := w.Write([]byte{','})
			n += nn
			if err != nil {
				return n, err
			}
		}
		b = []byte(strconv.Itoa(id))
		nn, err = w.Write(b)
		n += nn
		if err != nil {
			return n, err
		}
		first = false
	}

	// \n
	nn, err = w.Write([]byte{'\n'})
	n += nn
	if err != nil {
		return n, err
	}

	return n, nil
}

func main() {
	dir := flag.String("dir", ".", "каталог для сохранения файлов")
	flag.Parse()

	rand.Seed(time.Now().UnixNano())

	startDay := time.Now().UTC()
	startDay = time.Date(startDay.Year(), startDay.Month(), startDay.Day(), 0, 0, 0, 0, time.UTC)

	for i := 0; i < numFiles; i++ {
		ts := startDay.Add(time.Duration(i) * time.Minute)
		filename := ts.Format("20060102150405") + ".tsv.gz"
		path := filepath.Join(*dir, filename)

		log.Printf("generating %s ...", path)

		f, err := os.Create(path)
		if err != nil {
			log.Fatalf("cannot create file %s: %v", path, err)
		}

		gz, err := gzip.NewWriterLevel(f, gzip.BestSpeed)
		if err != nil {
			f.Close()
			log.Fatalf("cannot create gzip writer: %v", err)
		}

		written := int64(0)
		for written < fileSize {
			n, err := genLine(gz)
			if err != nil {
				log.Fatalf("error writing line: %v", err)
			}
			written += int64(n)
		}

		gz.Close()
		f.Close()

		log.Printf("generated %s (%.1f MB uncompressed)", path, float64(written)/(1024*1024))
	}

	log.Println("generation finished")
}
