package main

import (
	"fmt"

	"github.com/google/uuid"
)

func main() {
	fmt.Println("Hello!")
	fmt.Println(NewID())
}

func Add(a, b int) int {
	return a + b
}

func NewID() string {
	return uuid.NewString()
}
