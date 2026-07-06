package main

import (
	"compress/gzip"
	"os"
	"path/filepath"
	"testing"
)

func TestProcessLine_EmptyLine(t *testing.T) {
	deviceMemc := map[string]string{"idfa": "127.0.0.1:11211"}
	setter := NewMemcachedSetter(NewMemcachedPool(), true)

	res := ProcessLine("", deviceMemc, setter)
	if !res.Success {
		t.Error("expected success for empty line")
	}
	if res.IsError {
		t.Error("expected no error for empty line")
	}
}

func TestProcessLine_ValidLineDryRun(t *testing.T) {
	line := "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43"
	deviceMemc := map[string]string{"idfa": "127.0.0.1:11211"}
	setter := NewMemcachedSetter(NewMemcachedPool(), true)

	res := ProcessLine(line, deviceMemc, setter)
	if !res.Success {
		t.Error("expected success for valid line in dry run")
	}
	if res.IsError {
		t.Error("expected no error for valid line")
	}
}

func TestProcessLine_UnknownDeviceType(t *testing.T) {
	line := "unknown\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43"
	deviceMemc := map[string]string{"idfa": "127.0.0.1:11211"}
	setter := NewMemcachedSetter(NewMemcachedPool(), true)

	res := ProcessLine(line, deviceMemc, setter)
	if res.Success {
		t.Error("expected failure for unknown device type")
	}
	if !res.IsError {
		t.Error("expected error for unknown device type")
	}
}

func TestProcessLine_InvalidLine(t *testing.T) {
	line := "invalid_line"
	deviceMemc := map[string]string{"idfa": "127.0.0.1:11211"}
	setter := NewMemcachedSetter(NewMemcachedPool(), true)

	res := ProcessLine(line, deviceMemc, setter)
	if res.Success {
		t.Error("expected failure for invalid line")
	}
	if !res.IsError {
		t.Error("expected error for invalid line")
	}
}

func TestDotRename(t *testing.T) {
	tmpDir := t.TempDir()

	testFile := filepath.Join(tmpDir, "test.txt")
	err := os.WriteFile(testFile, []byte("test"), 0644)
	if err != nil {
		t.Fatalf("cannot create test file: %v", err)
	}

	err = DotRename(testFile)
	if err != nil {
		t.Fatalf("DotRename failed: %v", err)
	}

	if _, err := os.Stat(testFile); !os.IsNotExist(err) {
		t.Error("original file should not exist after rename")
	}

	renamed := filepath.Join(tmpDir, ".test.txt")
	if _, err := os.Stat(renamed); os.IsNotExist(err) {
		t.Error("renamed file should exist")
	}
}

func TestProcessFile_DryRun(t *testing.T) {
	tmpDir := t.TempDir()

	// Создаём тестовый TSV.gz файл.
	testFile := filepath.Join(tmpDir, "20170929000000.tsv.gz")
	f, err := os.Create(testFile)
	if err != nil {
		t.Fatalf("cannot create test file: %v", err)
	}

	gz := gzip.NewWriter(f)
	_, err = gz.Write([]byte("idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424\n\nidfa\t2rfw452y52g2gq4g\t-10.5\t20.3\t100,200\n"))
	if err != nil {
		f.Close()
		t.Fatalf("cannot write to test file: %v", err)
	}
	gz.Close()
	f.Close()

	deviceMemc := map[string]string{
		"idfa": "127.0.0.1:33013",
		"gaid": "127.0.0.1:33014",
		"adid": "127.0.0.1:33015",
		"dvid": "127.0.0.1:33016",
	}
	setter := NewMemcachedSetter(NewMemcachedPool(), true)

	processed, errors := ProcessFile(testFile, deviceMemc, setter, 4)

	if processed != 3 {
		t.Errorf("expected 3 processed records, got %d", processed)
	}
	if errors != 0 {
		t.Errorf("expected 0 errors, got %d", errors)
	}
}

func TestProcessFile_EmptyFile(t *testing.T) {
	tmpDir := t.TempDir()

	testFile := filepath.Join(tmpDir, "empty.tsv.gz")
	f, err := os.Create(testFile)
	if err != nil {
		t.Fatalf("cannot create test file: %v", err)
	}
	gz := gzip.NewWriter(f)
	gz.Close()
	f.Close()

	deviceMemc := map[string]string{"idfa": "127.0.0.1:33013"}
	setter := NewMemcachedSetter(NewMemcachedPool(), true)

	processed, errors := ProcessFile(testFile, deviceMemc, setter, 4)

	if processed != 0 {
		t.Errorf("expected 0 processed records, got %d", processed)
	}
	if errors != 0 {
		t.Errorf("expected 0 errors, got %d", errors)
	}
}

func TestProcessFile_NonExistentFile(t *testing.T) {
	deviceMemc := map[string]string{"idfa": "127.0.0.1:33013"}
	setter := NewMemcachedSetter(NewMemcachedPool(), true)

	processed, errors := ProcessFile("/nonexistent/file.tsv.gz", deviceMemc, setter, 4)

	if processed != 0 {
		t.Errorf("expected 0 processed records, got %d", processed)
	}
}

func TestCheckErrorRate(t *testing.T) {
	// Не должен паниковать.
	CheckErrorRate(100, 0)
	CheckErrorRate(100, 1)
	CheckErrorRate(100, 50)
	CheckErrorRate(0, 0)
}

func TestMemcachedPool_GetClient(t *testing.T) {
	pool := NewMemcachedPool()

	client1 := pool.GetClient("127.0.0.1:11211")
	if client1 == nil {
		t.Fatal("expected non-nil client")
	}

	// Проверяем повторное использование.
	client2 := pool.GetClient("127.0.0.1:11211")
	if client1 != client2 {
		t.Error("expected the same client for the same address")
	}

	// Проверяем разные клиенты для разных адресов.
	client3 := pool.GetClient("127.0.0.1:11212")
	if client1 == client3 {
		t.Error("expected different clients for different addresses")
	}
}

func TestProtoTest(t *testing.T) {
	// Не должен паниковать.
	ProtoTest()
}
