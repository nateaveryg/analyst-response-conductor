package rag

import (
	"context"
	"sync"
	"testing"
)

func TestParallelSpreadsheetIngestionConcurrency(t *testing.T) {
	ragSvc := NewRAGService()
	ctx := context.Background()

	progress, err := ragSvc.IngestSpreadsheetParallel(ctx, "DevSecOps Platforms, 2026", "ws-1", 4)
	if err != nil {
		t.Fatalf("unexpected error during parallel ingestion: %v", err)
	}

	if progress.TotalTabs != 4 {
		t.Errorf("expected 4 tabs, got %d", progress.TotalTabs)
	}
	if progress.TotalQuestions <= 0 {
		t.Errorf("expected questions > 0, got %d", progress.TotalQuestions)
	}
	if progress.AverageGrounding < 90.0 {
		t.Errorf("expected average grounding >= 90.0, got %.2f", progress.AverageGrounding)
	}
}

func TestConcurrentGoroutineRaceSafety(t *testing.T) {
	ragSvc := NewRAGService()
	ctx := context.Background()
	var wg sync.WaitGroup

	numWorkers := 20
	for i := 0; i < numWorkers; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			_, err := ragSvc.IngestSpreadsheetParallel(ctx, "Universal RFI Sheet", "ws-race-test", 8)
			if err != nil {
				t.Errorf("worker %d failed: %v", id, err)
			}
		}(i)
	}
	wg.Wait()
}

func BenchmarkMultiTabSpreadsheetIngestion(b *testing.B) {
	ragSvc := NewRAGService()
	ctx := context.Background()

	b.ResetTimer()
	b.ReportAllocs()

	for i := 0; i < b.N; i++ {
		_, err := ragSvc.IngestSpreadsheetParallel(ctx, "Gartner CNAP Multi-Tab Spreadsheet", "bench-ws", 8)
		if err != nil {
			b.Fatalf("benchmark failed: %v", err)
		}
	}
}
