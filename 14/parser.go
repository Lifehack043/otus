package main

import (
	"math"
	"strconv"
	"strings"
)

// AppsInstalled представляет распарсенную строку из TSV файла с данными об устройствах.
type AppsInstalled struct {
	DevType string    // тип устройства: idfa, gaid, adid, dvid
	DevID   string    // идентификатор устройства
	Lat     float64   // широта
	Lon     float64   // долгота
	Apps    []uint32  // список ID установленных приложений
}

// ParseAppsInstalled парсит строку TSV в объект AppsInstalled.
// Возвращает nil, если строка невалидна.
func ParseAppsInstalled(line string) *AppsInstalled {
	line = strings.TrimSpace(line)
	if line == "" {
		return nil
	}

	parts := strings.SplitN(line, "\t", 5)
	if len(parts) < 5 {
		return nil
	}

	devType := parts[0]
	devID := parts[1]
	if devType == "" || devID == "" {
		return nil
	}

	lat, err := strconv.ParseFloat(parts[2], 64)
	if err != nil {
		return nil
	}

	lon, err := strconv.ParseFloat(parts[3], 64)
	if err != nil {
		return nil
	}

	apps := parseApps(parts[4])

	return &AppsInstalled{
		DevType: devType,
		DevID:   devID,
		Lat:     lat,
		Lon:     lon,
		Apps:    apps,
	}
}

// parseApps парсит CSV строку с ID приложений.
// Возвращает список валидных ID приложений.
func parseApps(raw string) []uint32 {
	parts := strings.Split(raw, ",")
	apps := make([]uint32, 0, len(parts))

	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		v, err := strconv.ParseUint(p, 10, 32)
		if err != nil {
			continue
		}
		apps = append(apps, uint32(v))
	}

	return apps
}

// SerializeUserApps сериализует данные в protobuf-подобный бинарный формат.
// Формат соответствует proto2/3 message UserApps:
// - поле 1 (apps, repeated uint32): wire type 2 (length-delimited) с packed varint
// - поле 2 (lat, double): wire type 1 (64-bit)
// - поле 3 (lon, double): wire type 1 (64-bit)
func SerializeUserApps(apps []uint32, lat, lon float64) []byte {
	// Оцениваем размер: каждый app ~2-3 байта varint, заголовок поля ~1 байт
	// lat и lon по 10 байт каждый (1 байт tag + 8 байт double + 1 байт запас)
	capacity := len(apps)*3 + 20
	buf := make([]byte, 0, capacity)

	// Поле 1 (apps) - wire type 2 (length-delimited), packed repeated
	inner := make([]byte, 0, len(apps)*3)
	for _, app := range apps {
		inner = appendVarint(inner, app)
	}
	buf = append(buf, (1<<3)|2) // field 1, wire type 2
	buf = appendVarint(buf, uint64(len(inner)))
	buf = append(buf, inner...)

	// Поле 2 (lat) - wire type 1 (64-bit)
	buf = append(buf, (2<<3)|1) // field 2, wire type 1
	buf = appendFloat64LE(buf, lat)

	// Поле 3 (lon) - wire type 1 (64-bit)
	buf = append(buf, (3<<3)|1) // field 3, wire type 1
	buf = appendFloat64LE(buf, lon)

	return buf
}

// appendVarint добавляет varint-кодированное значение в буфер.
func appendVarint(buf []byte, v uint64) []byte {
	for v >= 0x80 {
		buf = append(buf, byte(v)|0x80)
		v >>= 7
	}
	buf = append(buf, byte(v))
	return buf
}

// appendFloat64LE добавляет float64 в little-endian формате.
func appendFloat64LE(buf []byte, v float64) []byte {
	bits := math.Float64bits(v)
	return append(
		buf,
		byte(bits),
		byte(bits>>8),
		byte(bits>>16),
		byte(bits>>24),
		byte(bits>>32),
		byte(bits>>40),
		byte(bits>>48),
		byte(bits>>56),
	)
}
