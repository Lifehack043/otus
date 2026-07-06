package main

import (
	"sync"

	"github.com/bradfitz/gomemcache/memcache"
)

// DefaultMemcachedAddrs содержит адреса Memcached по умолчанию для каждого типа устройства.
var DefaultMemcachedAddrs = map[string]string{
	"idfa": "127.0.0.1:33013",
	"gaid": "127.0.0.1:33014",
	"adid": "127.0.0.1:33015",
	"dvid": "127.0.0.1:33016",
}

// getMemcachedAddr возвращает адрес Memcached для указанного типа устройства.
func getMemcachedAddr(devType string) string {
	return DefaultMemcachedAddrs[devType]
}

// MemcachedPool — пул подключений к Memcached с разделением по адресам.
// Безопасен для конкурентного доступа.
type MemcachedPool struct {
	mu      sync.RWMutex
	clients map[string]*memcache.Client
}

// NewMemcachedPool создаёт новый пул подключений.
func NewMemcachedPool() *MemcachedPool {
	return &MemcachedPool{
		clients: make(map[string]*memcache.Client),
	}
}

// GetClient возвращает или создаёт клиент для указанного адреса Memcached.
func (p *MemcachedPool) GetClient(addr string) *memcache.Client {
	p.mu.RLock()
	client, ok := p.clients[addr]
	p.mu.RUnlock()
	if ok {
		return client
	}

	p.mu.Lock()
	defer p.mu.Unlock()
	// Double-check после захвата эксклюзивной блокировки.
	client, ok = p.clients[addr]
	if ok {
		return client
	}
	client = memcache.New(addr)
	p.clients[addr] = client
	return client
}

// MemcachedSetter инкапсулирует операцию записи в Memcached.
type MemcachedSetter struct {
	pool   *MemcachedPool
	dryRun bool
}

// NewMemcachedSetter создаёт новый setter.
func NewMemcachedSetter(pool *MemcachedPool, dryRun bool) *MemcachedSetter {
	return &MemcachedSetter{
		pool:   pool,
		dryRun: dryRun,
	}
}

// Set записывает данные об устройствах в Memcached.
// Возвращает true при успехе, false при ошибке.
func (s *MemcachedSetter) Set(devType, devID string, apps []uint32, lat, lon float64) bool {
	key := devType + ":" + devID
	data := SerializeUserApps(apps, lat, lon)

	if s.dryRun {
		return true
	}

	addr := getMemcachedAddr(devType)
	client := s.pool.GetClient(addr)
	err := client.Set(&memcache.Item{
		Key:   key,
		Value: data,
	})
	if err != nil {
		return false
	}
	return true
}
