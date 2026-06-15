# App Design Document: Litinerary, A Book-Oriented Tour Companion
1. Executive Summary
The proposed application is a digital companion designed to help literary enthusiasts plan personalized travel itineraries based on their favorite books. By leveraging Large Language Models (LLMs) and vector databases, the app translates narrative locations into actionable, real-world tour plans, complete with interactive maps and ticketing integration.
{{Add aparagraph: users will be able to tour with the help of the interactive map reading hteir itinerary  or  hearing thetheir itinerary narrated by an AI voice.}}

2. Target Audience & User Personas
The Literary Traveler: Users who travel specifically to visit sites related to their favorite authors or novels.

The Casual Tourist: Travelers looking for a unique, themed way to explore a new city.

The Local Explorer: Residents looking to rediscover their city through the lens of literature.

3. Business Logic & User Flows
3.1. User Account Management
Anonymous Access: Users can explore cities, view book recommendations, and generate basic itineraries without an account.

{{Add: those itineraries will be public and hosted in a repository of itineraries any user can search and use them}}

Registered Access: Account creation allows users to save preferences, bookmark itineraries, access history (via Vector DB), and sync data across devices.

3.2. Core User Journey
Destination Selection: The user inputs or selects a target city or region.

Book Discovery: The system presents a curated list of books set in or highly relevant to the chosen destination.

Tour Configuration: The user selects a specific book and defines their trip parameters:

Duration: Number of days for the visit.

Transportation Mode: Walking, Rented Car/Taxi, or Public Transportation.

Itinerary Generation: The app computes and returns a day-by-day itinerary.

Map Integration: A visual, interactive map displays the route, points of interest (POIs), and daily paths.

Ticketing & Logistics: For POIs requiring entry fees, the app displays estimated costs and direct links to purchase tickets or book tours.

4. Technical Architecture
The application follows a modern decoupled architecture, ensuring scalability and responsiveness.

4.1. Frontend (User Interface)

{{ADD: use the static website in folder docs/webpage-template as a template for the frontend}}

Framework: Vue.js

Language: TypeScript

Key Libraries:

Vue Router for navigation.

Pinia for state management (handling user preferences and current itinerary state).

Mapbox GL JS or Leaflet for interactive map rendering.

Component library (e.g., Vuetify or Tailwind UI) for rapid UI development.

4.2. Backend (API & Business Logic)
Framework: Python FastAPI

Role: Acts as the central orchestrator, managing API requests from the frontend, interfacing with the LLM, querying the Vector DB, and integrating with third-party APIs (Maps, Ticketing).

4.3. AI & Data Pipeline
LLM Engine: Processing books (ingestion phase) to extract geographical entities, historical context, and narrative significance. During runtime, it constructs the logical daily itinerary.

Vector Database: (e.g., Pinecone, Milvus, or Qdrant)

{{ADD: free generated itineraries as save in a database and presented to users in a repository page. For free users the app will look at the database if there is an itinerary matching the requested city, book, numer of days and means of transportation. If an itinerary only match partialy the app will adapt it to the requested itinerary. If there is no itinerary that matches the request the app will generate one}}

{{Add: Subscribers will have access to a chat with the app to generate a tailored visit.}}

Search & Retrieval: Caches previously generated itineraries and book-to-city mappings to reduce LLM compute costs.

Personalization: Stores user preferences as embeddings to improve future book and POI recommendations.

POI Search API: (e.g., Google Places API or Foursquare API) Verifies LLM-extracted locations against real-world data to ensure accuracy, fetch operating hours, and retrieve ticketing links.

5. LLM & Data Strategy Deep Dive
5.1. Book Ingestion & Processing
Due to context window limits and copyright considerations, the LLM will rely on comprehensive book summaries, location indexes, and open-source texts (Project Gutenberg) where applicable.

Information Extraction: The LLM identifies specific addresses, landmarks, neighborhoods, and routes mentioned in the text.

5.2. Itinerary Generation Algorithm
Filtering: Filter POIs based on the chosen transportation mode (e.g., cluster walking POIs tightly; allow wider radius for car rentals).

Pacing: Distribute POIs evenly across the requested number of days.

Routing: Optimize the daily path to minimize backtracking (solving a constrained Traveling Salesperson Problem, assisted by routing APIs).

{{Add: a judge llm to review the newlly generated itineraries: it the itinerary factible? can a person walk said distances? was the llm who created the itinerary having delusions? only itineraries approved by the judge will be presented to the user. users will have an oportunity to review the itinerary and and the llms will take the reviews into consideration to improve the itinerary.}}

6. API Endpoints (Draft)
GET /api/destinations - Fetch supported cities/regions.

GET /api/books?city={city_id} - Retrieve books relevant to a destination.

POST /api/itinerary/generate - Submit book ID, days, and transport mode; returns the JSON itinerary.

POST /api/users/preferences - Save user embedding data to Vector DB.

POST /api/users/reviews - save reviews to Vector DB to improve itineraries. 

7. Future Milestones
Phase 1: MVP with 5 major cities and public domain literature.

Phase 2: Integration of Vector DB for personalized recommendations and user accounts.

Phase 3: Affiliate partnerships for ticketing and tour bookings to drive revenue.

Phase 4: E-commerce integration to allow users to purchase physical copies, eBooks, or audiobooks directly through the app (via affiliate links or direct storefront).