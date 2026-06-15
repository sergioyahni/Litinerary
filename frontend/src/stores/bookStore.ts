import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { fetchBooksByDestination } from "../services/booksApi";
import type { Book } from "../types";

export const useBookStore = defineStore("books", () => {
  const books = ref<Book[]>([]);
  const selectedBookId = ref<string | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const selectedBook = computed(
    () => books.value.find((book) => book.id === selectedBookId.value) ?? null,
  );
  const hasBooks = computed(() => books.value.length > 0);

  async function loadBooks(destinationId: string): Promise<void> {
    isLoading.value = true;
    error.value = null;
    selectedBookId.value = null;

    try {
      books.value = await fetchBooksByDestination(destinationId);
    } catch (caught) {
      books.value = [];
      error.value = caught instanceof Error ? caught.message : "Unable to load books.";
    } finally {
      isLoading.value = false;
    }
  }

  function selectBook(bookId: string): void {
    selectedBookId.value = bookId;
  }

  function clearBooks(): void {
    books.value = [];
    selectedBookId.value = null;
    error.value = null;
  }

  function reset(): void {
    books.value = [];
    selectedBookId.value = null;
    isLoading.value = false;
    error.value = null;
  }

  return {
    books,
    selectedBook,
    selectedBookId,
    hasBooks,
    isLoading,
    error,
    loadBooks,
    selectBook,
    clearBooks,
    reset,
  };
});
