package main

import (
	"flag"
	"log"
	"os"
	"path/filepath"
	"sort"
)

// config содержит конфигурацию приложения.
type config struct {
	pattern string
	dry     bool
	test    bool
	logFile string
	workers int
	idfa    string
	gaid    string
	adid    string
	dvid    string
}

func parseConfig() *config {
	cfg := &config{}

	flag.StringVar(&cfg.pattern, "pattern", "/data/appsinstalled/*.tsv.gz",
		"паттерн для поиска TSV.gz файлов")
	flag.BoolVar(&cfg.dry, "dry", false,
		"режим сухого запуска (только логирование)")
	flag.BoolVar(&cfg.test, "test", false,
		"запуск теста сериализации")
	flag.StringVar(&cfg.logFile, "log", "",
		"путь к файлу логов (пусто = stdout)")
	flag.IntVar(&cfg.workers, "workers", 16,
		"количество рабочих горутин")
	flag.StringVar(&cfg.idfa, "idfa", "127.0.0.1:33013",
		"адрес Memcached для IDFA устройств")
	flag.StringVar(&cfg.gaid, "gaid", "127.0.0.1:33014",
		"адрес Memcached для GAID устройств")
	flag.StringVar(&cfg.adid, "adid", "127.0.0.1:33015",
		"адрес Memcached для ADID устройств")
	flag.StringVar(&cfg.dvid, "dvid", "127.0.0.1:33016",
		"адрес Memcached для DVID устройств")

	flag.Parse()

	return cfg
}

func setupLogging(cfg *config) {
	var w *os.File
	if cfg.logFile != "" {
		f, err := os.OpenFile(cfg.logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
		if err != nil {
			log.Fatalf("cannot open log file: %v", err)
		}
		w = f
	} else {
		w = os.Stdout
	}

	log.SetOutput(w)
	log.SetFlags(log.Ldate | log.Ltime)
}

func main() {
	cfg := parseConfig()
	setupLogging(cfg)

	if cfg.test {
		ProtoTest()
		log.Println("proto test passed")
		return
	}

	log.Printf("Memc loader started with options: pattern=%s dry=%v workers=%d idfa=%s gaid=%s adid=%s dvid=%s",
		cfg.pattern, cfg.dry, cfg.workers, cfg.idfa, cfg.gaid, cfg.adid, cfg.dvid)

	deviceMemc := map[string]string{
		"idfa": cfg.idfa,
		"gaid": cfg.gaid,
		"adid": cfg.adid,
		"dvid": cfg.dvid,
	}

	// Обновляем глобальные адреса для сериализации.
	DefaultMemcachedAddrs["idfa"] = cfg.idfa
	DefaultMemcachedAddrs["gaid"] = cfg.gaid
	DefaultMemcachedAddrs["adid"] = cfg.adid
	DefaultMemcachedAddrs["dvid"] = cfg.dvid

	// Находим и сортируем файлы для хронологической обработки.
	files, err := filepath.Glob(cfg.pattern)
	if err != nil {
		log.Fatalf("error globbing pattern %s: %v", cfg.pattern, err)
	}
	sort.Strings(files)

	if len(files) == 0 {
		log.Printf("no files matched pattern: %s", cfg.pattern)
		return
	}

	pool := NewMemcachedPool()
	setter := NewMemcachedSetter(pool, cfg.dry)

	for _, fn := range files {
		log.Printf("processing %s", fn)

		processed, errors := ProcessFile(fn, deviceMemc, setter, cfg.workers)

		if processed == 0 {
			log.Printf("no records processed in %s, renaming anyway", fn)
			if err := DotRename(fn); err != nil {
				log.Printf("error renaming %s: %v", fn, err)
			}
			continue
		}

		CheckErrorRate(processed, errors)

		if err := DotRename(fn); err != nil {
			log.Printf("error renaming %s: %v", fn, err)
		}
	}

	log.Println("Memc loader finished")
}
