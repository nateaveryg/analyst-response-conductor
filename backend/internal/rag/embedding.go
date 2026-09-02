package rag

import (
	"math"
)

type EmbeddingService struct {
	Dimensions int
}

func NewEmbeddingService() *EmbeddingService {
	return &EmbeddingService{Dimensions: 768}
}

func CosineSimilarity(a, b []float32) float64 {
	if len(a) != len(b) || len(a) == 0 {
		return 0.0
	}
	var dotProduct, normA, normB float64
	for i := range a {
		valA := float64(a[i])
		valB := float64(b[i])
		dotProduct += valA * valB
		normA += valA * valA
		normB += valB * valB
	}
	if normA == 0 || normB == 0 {
		return 0.0
	}
	return dotProduct / (math.Sqrt(normA) * math.Sqrt(normB))
}

// GenerateDeterministicEmbedding produces deterministic 768-d unit vectors from text hash
func (s *EmbeddingService) GenerateDeterministicEmbedding(text string) []float32 {
	vec := make([]float32, s.Dimensions)
	if text == "" {
		return vec
	}

	var sum float64
	for i := 0; i < s.Dimensions; i++ {
		charIdx := i % len(text)
		val := float32(float64(text[charIdx]) * math.Sin(float64(i+1)*0.1))
		vec[i] = val
		sum += float64(val * val)
	}

	norm := math.Sqrt(sum)
	if norm > 0 {
		for i := range vec {
			vec[i] = float32(float64(vec[i]) / norm)
		}
	}
	return vec
}
