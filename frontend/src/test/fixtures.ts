import type { Book, Destination, Itinerary } from "../types";

export const destinationFixture: Destination = {
  id: "london",
  name: "London",
  country: "United Kingdom",
  description: "A literary city.",
  latitude: 51.5072,
  longitude: -0.1276,
  supported: true,
};

export const bookFixture: Book = {
  id: "oliver-twist",
  destinationIds: ["london"],
  title: "Oliver Twist",
  author: "Charles Dickens",
  description: "A Dickens route.",
  publicationYear: 1838,
  publicDomain: true,
  themes: ["classic"],
};

export const itineraryFixture: Itinerary = {
  id: "it-london-oliver-twist-1-walking",
  destinationId: "london",
  bookId: "oliver-twist",
  title: "Oliver Twist in London",
  summary: "A compact Dickensian walk.",
  durationDays: 1,
  transportationMode: "walking",
  isPublic: true,
  generatedFrom: "exact_match",
  sourceType: "exact_match",
  sourceItineraryId: "it-london-oliver-twist-1-walking",
  adaptationNotes: ["Returned from the public repository."],
  createdAt: "2026-06-10T00:00:00.000Z",
  days: [
    {
      id: "day-1",
      dayNumber: 1,
      title: "Markets, Alleys, and Dickens' London",
      summary: "Follow a short route through Dickensian London.",
      estimatedDurationHours: 2,
      stops: [
        {
          id: "stop-1",
          order: 1,
          title: "Start at Smithfield Market",
          narrativeNote: "Begin with the bustle of trade.",
          logisticsNote: "Good morning starting point.",
          poi: {
            id: "smithfield-market",
            destinationId: "london",
            bookIds: ["oliver-twist"],
            name: "Smithfield Market",
            description: "A historic market district.",
            latitude: 51.5188,
            longitude: -0.1026,
            estimatedDurationMinutes: 35,
            ticketingNote: "Outdoor/public area; no ticket required.",
            literaryRelevance: "Grounds Oliver Twist in working London.",
            verificationStatus: "mock",
          },
        },
      ],
    },
  ],
};
