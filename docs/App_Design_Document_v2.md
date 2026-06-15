# App Design Document: Litinerary, A Book-Oriented Tour Companion

## 1. Executive Summary

The proposed application is a digital companion designed to help literary enthusiasts plan personalized travel itineraries based on their favorite books. By leveraging Large Language Models (LLMs) and vector databases, the app translates narrative locations into actionable, real-world tour plans, complete with interactive maps and ticketing integration.

Users will be able to follow their tours with the help of an interactive map while reading their itinerary on screen or listening to the itinerary narrated by an AI voice. This creates a flexible experience for travelers who prefer either visual guidance, text-based exploration, or hands-free audio storytelling while moving through a destination.

## 2. Target Audience & User Personas

**The Literary Traveler:** Users who travel specifically to visit sites related to their favorite authors or novels.

**The Casual Tourist:** Travelers looking for a unique, themed way to explore a new city.

**The Local Explorer:** Residents looking to rediscover their city through the lens of literature.

## 3. Business Logic & User Flows

### 3.1. User Account Management

**Anonymous Access:** Users can explore cities, view book recommendations, and generate basic itineraries without an account.

Free generated itineraries will be public and hosted in a searchable itinerary repository. Any user will be able to search, browse, and reuse these public itineraries.

**Registered Access:** Account creation allows users to save preferences, bookmark itineraries, access history via the Vector DB, and sync data across devices.

### 3.2. Core User Journey

**Destination Selection:** The user inputs or selects a target city or region.

**Book Discovery:** The system presents a curated list of books set in or highly relevant to the chosen destination.

**Tour Configuration:** The user selects a specific book and defines their trip parameters:

- **Duration:** Number of days for the visit.
- **Transportation Mode:** Walking, rented car/taxi, or public transportation.

**Itinerary Generation:** The app computes and returns a day-by-day itinerary.

**Map Integration:** A visual, interactive map displays the route, points of interest (POIs), and daily paths.

**Ticketing & Logistics:** For POIs requiring entry fees, the app displays estimated costs and direct links to purchase tickets or book tours.

## 4. Technical Architecture

The application follows a modern decoupled architecture, ensuring scalability and responsiveness.

### 4.1. Frontend (User Interface)

The frontend should use the static website located in `docs/webpage-template` as the visual and structural template for the initial user interface. The static template should guide the layout, page structure, styling direction, and overall user experience before the app is progressively converted into a dynamic Vue.js implementation.

**Framework:** Vue.js

**Language:** TypeScript

**Key Libraries:**

- Vue Router for navigation.
- Pinia for state management, handling user preferences and current itinerary state.
- Mapbox GL JS or Leaflet for interactive map rendering.
- Component library, such as Vuetify or Tailwind UI, for rapid UI development.

### 4.2. Backend (API & Business Logic)

**Framework:** Python FastAPI

**Role:** Acts as the central orchestrator, managing API requests from the frontend, interfacing with the LLM, querying the Vector DB, and integrating with third-party APIs such as maps and ticketing services.

### 4.3. AI & Data Pipeline

**LLM Engine:** Processes books during the ingestion phase to extract geographical entities, historical context, and narrative significance. During runtime, it constructs the logical daily itinerary.

**Vector Database:** Pinecone, Milvus, Qdrant, or an equivalent vector database.

**Public Itinerary Repository:** Free generated itineraries will be saved in a database and presented to users through a repository page. For free users, the app will first search the database for an itinerary matching the requested city, book, number of days, and means of transportation. If a matching itinerary is found, the app will return it. If the match is only partial, the app will adapt the existing itinerary to fit the requested parameters. If no suitable itinerary exists, the app will generate a new itinerary and save it to the repository.

**Subscriber Chat Experience:** Subscribers will have access to an interactive chat with the app, allowing them to generate a more tailored visit through conversational refinement.

**Search & Retrieval:** Caches previously generated itineraries and book-to-city mappings to reduce LLM compute costs.

**Personalization:** Stores user preferences as embeddings to improve future book and POI recommendations.

**POI Search API:** Google Places API, Foursquare API, or a similar service verifies LLM-extracted locations against real-world data to ensure accuracy, fetch operating hours, and retrieve ticketing links.

## 5. LLM & Data Strategy Deep Dive

### 5.1. Book Ingestion & Processing

Due to context window limits and copyright considerations, the LLM will rely on comprehensive book summaries, location indexes, and open-source texts, such as Project Gutenberg texts, where applicable.

**Information Extraction:** The LLM identifies specific addresses, landmarks, neighborhoods, and routes mentioned in the text.

### 5.2. Itinerary Generation Algorithm

**Filtering:** Filter POIs based on the chosen transportation mode. For example, walking itineraries should cluster POIs tightly, while car or taxi itineraries can support a wider radius.

**Pacing:** Distribute POIs evenly across the requested number of days.

**Routing:** Optimize the daily path to minimize backtracking by solving a constrained Traveling Salesperson Problem assisted by routing APIs.

**LLM Judge Review:** Newly generated itineraries will be reviewed by a judge LLM before being presented to users. The judge LLM will evaluate whether the itinerary is feasible, whether the walking distances are realistic, whether the routing is practical, and whether the generating LLM introduced hallucinated or unsupported details. Only itineraries approved by the judge LLM will be presented to the user.

**User Review Feedback Loop:** Users will have an opportunity to review itineraries after generation or use. These reviews will be stored and used by the LLM pipeline to improve future itinerary quality, feasibility, and personalization.

## 6. API Endpoints (Draft)

`GET /api/destinations` - Fetch supported cities/regions.

`GET /api/books?city={city_id}` - Retrieve books relevant to a destination.

`POST /api/itinerary/generate` - Submit book ID, days, and transport mode; returns the JSON itinerary.

`GET /api/itineraries` - Search and retrieve public itineraries from the itinerary repository.

`POST /api/itineraries/adapt` - Adapt an existing public itinerary to match a user's requested city, book, duration, or transportation mode.

`POST /api/users/preferences` - Save user embedding data to the Vector DB.

`POST /api/users/reviews` - Save reviews to the Vector DB to improve itineraries.

`POST /api/subscribers/chat` - Enable subscribers to chat with the app for tailored itinerary generation and refinement.

## 7. Future Milestones

**Phase 1:** MVP with 5 major cities and public domain literature.

**Phase 2:** Integration of Vector DB for personalized recommendations, public itinerary repository, and user accounts.

**Phase 3:** Subscriber chat experience, AI voice narration, and LLM judge validation pipeline.

**Phase 4:** Affiliate partnerships for ticketing and tour bookings to drive revenue.

**Phase 5:** E-commerce integration to allow users to purchase physical copies, eBooks, or audiobooks directly through the app via affiliate links or direct storefront.
