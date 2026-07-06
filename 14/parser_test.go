package main

import (
	"testing"
)

func TestParseAppsInstalled_ValidIDFA(t *testing.T) {
	line := "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23"
	result := ParseAppsInstalled(line)

	if result == nil {
		t.Fatal("expected non-nil result")
	}
	if result.DevType != "idfa" {
		t.Errorf("expected devType 'idfa', got '%s'", result.DevType)
	}
	if result.DevID != "1rfw452y52g2gq4g" {
		t.Errorf("expected devID '1rfw452y52g2gq4g', got '%s'", result.DevID)
	}
	if result.Lat != 55.55 {
		t.Errorf("expected lat 55.55, got %f", result.Lat)
	}
	if result.Lon != 42.42 {
		t.Errorf("expected lon 42.42, got %f", result.Lon)
	}
	expectedApps := []uint32{1423, 43, 567, 3, 7, 23}
	if len(result.Apps) != len(expectedApps) {
		t.Fatalf("expected %d apps, got %d", len(expectedApps), len(result.Apps))
	}
	for i, app := range expectedApps {
		if result.Apps[i] != app {
			t.Errorf("expected app[%d] = %d, got %d", i, app, result.Apps[i])
		}
	}
}

func TestParseAppsInstalled_ValidGAID(t *testing.T) {
	line := "gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
	result := ParseAppsInstalled(line)

	if result == nil {
		t.Fatal("expected non-nil result")
	}
	if result.DevType != "gaid" {
		t.Errorf("expected devType 'gaid', got '%s'", result.DevType)
	}
	expectedApps := []uint32{7423, 424}
	if len(result.Apps) != len(expectedApps) {
		t.Fatalf("expected %d apps, got %d", len(expectedApps), len(result.Apps))
	}
}

func TestParseAppsInstalled_TooFewFields(t *testing.T) {
	line := "idfa\t1rfw452y52g2gq4g\t55.55"
	result := ParseAppsInstalled(line)
	if result != nil {
		t.Error("expected nil result for line with too few fields")
	}
}

func TestParseAppsInstalled_EmptyDevType(t *testing.T) {
	line := "\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43"
	result := ParseAppsInstalled(line)
	if result != nil {
		t.Error("expected nil result for empty devType")
	}
}

func TestParseAppsInstalled_EmptyDevID(t *testing.T) {
	line := "idfa\t\t55.55\t42.42\t1423,43"
	result := ParseAppsInstalled(line)
	if result != nil {
		t.Error("expected nil result for empty devID")
	}
}

func TestParseAppsInstalled_InvalidCoords(t *testing.T) {
	line := "idfa\t1rfw452y52g2gq4g\tabc\t42.42\t1423,43"
	result := ParseAppsInstalled(line)
	if result != nil {
		t.Error("expected nil result for invalid coordinates")
	}
}

func TestParseAppsInstalled_PartialInvalidApps(t *testing.T) {
	line := "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,abc,567"
	result := ParseAppsInstalled(line)
	if result == nil {
		t.Fatal("expected non-nil result")
	}
	expectedApps := []uint32{1423, 567}
	if len(result.Apps) != len(expectedApps) {
		t.Fatalf("expected %d apps, got %d", len(expectedApps), len(result.Apps))
	}
}

func TestParseAppsInstalled_EmptyLine(t *testing.T) {
	result := ParseAppsInstalled("")
	if result != nil {
		t.Error("expected nil result for empty line")
	}
}

func TestParseAppsInstalled_WhitespaceOnly(t *testing.T) {
	result := ParseAppsInstalled("   ")
	if result != nil {
		t.Error("expected nil result for whitespace-only line")
	}
}

func TestSerializeUserApps(t *testing.T) {
	apps := []uint32{1423, 43, 567, 3, 7, 23}
	lat := 55.55
	lon := 42.42

	data := SerializeUserApps(apps, lat, lon)
	if len(data) == 0 {
		t.Fatal("expected non-empty serialized data")
	}

	// Проверяем, что данные начинаются с тега поля 1 (apps).
	// field 1, wire type 2 = (1<<3)|2 = 0x0a
	if data[0] != 0x0a {
		t.Errorf("expected first byte 0x0a (field 1, wire type 2), got 0x%02x", data[0])
	}
}

func TestSerializeUserApps_EmptyApps(t *testing.T) {
	data := SerializeUserApps(nil, 0.0, 0.0)
	if len(data) == 0 {
		t.Fatal("expected non-empty serialized data even for empty apps")
	}
}

func TestAppendVarint(t *testing.T) {
	tests := []struct {
		input    uint64
		expected []byte
	}{
		{0, []byte{0x00}},
		{1, []byte{0x01}},
		{127, []byte{0x7f}},
		{128, []byte{0x80, 0x01}},
		{300, []byte{0xac, 0x02}},
	}

	for _, tc := range tests {
		buf := appendVarint(nil, tc.input)
		if len(buf) != len(tc.expected) {
			t.Errorf("varint(%d): expected length %d, got %d", tc.input, len(tc.expected), len(buf))
		}
		for i, b := range tc.expected {
			if buf[i] != b {
				t.Errorf("varint(%d)[%d]: expected 0x%02x, got 0x%02x", tc.input, i, b, buf[i])
			}
		}
	}
}

func TestParseApps(t *testing.T) {
	tests := []struct {
		input    string
		expected []uint32
	}{
		{"1,2,3", []uint32{1, 2, 3}},
		{"", nil},
		{"100", []uint32{100}},
		{"1,abc,3", []uint32{1, 3}},
		{" 1 , 2 , 3 ", []uint32{1, 2, 3}},
	}

	for _, tc := range tests {
		result := parseApps(tc.input)
		if len(result) != len(tc.expected) {
			t.Errorf("parseApps(%q): expected %d apps, got %d", tc.input, len(tc.expected), len(result))
			continue
		}
		for i, app := range tc.expected {
			if result[i] != app {
				t.Errorf("parseApps(%q)[%d]: expected %d, got %d", tc.input, i, app, result[i])
			}
		}
	}
}
