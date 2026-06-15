export type TransportationMode = "walking" | "public_transport" | "car_taxi";
export type VerificationStatus =
  | "mock"
  | "unverified"
  | "verified"
  | "mock_verified"
  | "provider_verified"
  | "needs_review"
  | "rejected";
export type ItineraryVisibility = "public" | "private" | "unlisted";
export type ItineraryCreatedByMode =
  | "anonymous"
  | "registered_user"
  | "subscriber"
  | "admin"
  | "seed";
export type ItinerarySourceType =
  | "exact_match"
  | "adapted_match"
  | "new_mock_generation";

export interface Destination {
  id: string;
  name: string;
  country: string;
  region?: string | null;
  description: string;
  latitude: number;
  longitude: number;
  imageUrl?: string | null;
  supported: boolean;
}

export interface AffiliateLink {
  title: string;
  sourceUrl: string;
  providerName?: string | null;
  providerType?: string;
  affiliate?: boolean;
  lastCheckedAt?: string | null;
  relevanceScore?: number | null;
}

export interface Book {
  id: string;
  destinationIds: string[];
  title: string;
  author: string;
  description: string;
  publicationYear?: number | null;
  publicDomain: boolean;
  themes: string[];
  coverUrl?: string | null;
  affiliateLinks?: AffiliateLink[];
}

export interface POI {
  id: string;
  destinationId: string;
  bookIds: string[];
  name: string;
  description: string;
  latitude: number;
  longitude: number;
  address?: string | null;
  estimatedDurationMinutes: number;
  ticketingNote?: string | null;
  literaryRelevance: string;
  verificationStatus: VerificationStatus;
  verificationProvider?: string | null;
  providerVersion?: string | null;
  providerRequestId?: string | null;
  verificationConfidence?: number | null;
  verifiedName?: string | null;
  verifiedAddress?: string | null;
  verifiedLatitude?: number | null;
  verifiedLongitude?: number | null;
  openingHoursNote?: string | null;
  ticketingUrl?: string | null;
  verificationNotes?: string[];
  lastVerifiedAt?: string | null;
  manualReviewStatus?: string;
  reviewedByUserId?: string | null;
  provenanceMetadata?: Record<string, unknown>;
}

export interface ItineraryStop {
  id: string;
  poi: POI;
  order: number;
  title: string;
  narrativeNote: string;
  logisticsNote?: string | null;
  estimatedStartTime?: string | null;
  estimatedEndTime?: string | null;
}

export interface ItineraryDay {
  id: string;
  dayNumber: number;
  title: string;
  summary: string;
  stops: ItineraryStop[];
  estimatedDistanceKm?: number | null;
  estimatedDurationHours?: number | null;
  routeGeometry?: number[][];
  routingProviderMetadata?: Record<string, unknown> | null;
  routingWarnings?: string[];
}

export interface Itinerary {
  id: string;
  destinationId: string;
  bookId: string;
  title: string;
  summary: string;
  durationDays: number;
  transportationMode: TransportationMode;
  days: ItineraryDay[];
  isPublic: boolean;
  ownerUserId?: string | null;
  visibility?: ItineraryVisibility;
  generatedFrom: "mock" | "exact_match" | "adapted" | "new_generation";
  sourceType?: ItinerarySourceType | null;
  sourceItineraryId?: string | null;
  createdByMode?: ItineraryCreatedByMode;
  createdByUserId?: string | null;
  subscriberOnly?: boolean;
  adaptationNotes?: string[];
  createdAt: string;
  updatedAt?: string | null;
  providerName?: string | null;
  providerType?: string | null;
  providerVersion?: string | null;
  providerRequestId?: string | null;
  generatedByService?: string | null;
  confidenceScore?: number | null;
  provenanceMetadata?: Record<string, unknown>;
}

export interface ItineraryGenerationRequest {
  destinationId: string;
  bookId: string;
  durationDays: number;
  transportationMode: TransportationMode;
}

export interface ItineraryGenerationResponse {
  itinerary: Itinerary;
  matchedExisting: boolean;
  sourceItineraryId?: string | null;
  message: string;
}

export interface ItineraryAdaptationRequest {
  sourceItineraryId: string;
  durationDays: number;
  transportationMode: TransportationMode;
}

export interface NarrationRequest {
  voiceStyle?: string;
  includePlaceholderAudio?: boolean;
}

export interface NarrationScript {
  itineraryId: string;
  title: string;
  text: string;
  estimatedDurationSeconds: number;
  providerName?: string | null;
  providerType?: string | null;
  providerVersion?: string | null;
  providerRequestId?: string | null;
  provenanceMetadata?: Record<string, unknown>;
}

export interface AudioMetadata {
  available: boolean;
  url?: string | null;
  format?: string | null;
  durationSeconds?: number | null;
  providerName: string;
  providerType: string;
  providerVersion: string;
  placeholder: boolean;
  warnings: string[];
}

export interface ItineraryNarration {
  itineraryId: string;
  script: NarrationScript;
  audio: AudioMetadata;
  format: "text_only" | "placeholder_audio";
}

export type ChatMessageRole = "user" | "assistant" | "system";
export type ChatSessionStatus = "active" | "archived";

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: ChatMessageRole;
  content: string;
  createdAt: string;
  providerName?: string | null;
  providerType?: string | null;
  providerVersion?: string | null;
  providerRequestId?: string | null;
  provenanceMetadata?: Record<string, unknown>;
}

export interface ChatItineraryReference {
  id: string;
  sessionId: string;
  itineraryId: string;
  sourceItineraryId?: string | null;
  refinementPrompt: string;
  createdAt: string;
  providerName?: string | null;
  providerType?: string | null;
  providerVersion?: string | null;
  providerRequestId?: string | null;
  confidenceScore?: number | null;
  provenanceMetadata?: Record<string, unknown>;
}

export interface ChatSession {
  id: string;
  userId: string;
  title: string;
  status: ChatSessionStatus;
  createdAt: string;
  updatedAt: string;
  providerName?: string | null;
  providerType?: string | null;
  providerVersion?: string | null;
  providerRequestId?: string | null;
  provenanceMetadata?: Record<string, unknown>;
  messages: ChatMessage[];
  itineraryReferences: ChatItineraryReference[];
}

export interface ChatSessionCreate {
  title?: string | null;
}

export interface ChatMessageCreate {
  content: string;
}

export interface ChatMessageResponse {
  session: ChatSession;
  messages: ChatMessage[];
}

export interface ChatItineraryRefinementRequest {
  sourceItineraryId: string;
  prompt: string;
  durationDays?: number | null;
  transportationMode?: TransportationMode | null;
}

export interface ChatItineraryRefinementResponse {
  session: ChatSession;
  itinerary: Itinerary;
  reference: ChatItineraryReference;
  message: ChatMessage;
}

export interface UserCreateRequest {
  id?: string;
  email?: string | null;
  displayName?: string | null;
}

export interface UserPreferenceUpsertRequest {
  key: string;
  value: Record<string, unknown>;
}

export interface UserPreference {
  id: string;
  userId: string;
  key: string;
  value: Record<string, unknown>;
  createdAt: string;
}

export interface UserReviewCreateRequest {
  itineraryId: string;
  rating?: number;
  comment?: string;
}

export interface UserReview {
  id: string;
  userId: string;
  itineraryId?: string | null;
  rating?: number | null;
  comment?: string | null;
  createdAt: string;
}

export interface UserProfile {
  id: string;
  email?: string | null;
  displayName?: string | null;
  authProvider?: string | null;
  role?: string;
  subscriptionStatus?: string;
  createdAt: string;
  updatedAt?: string | null;
  preferences: UserPreference[];
  reviews: UserReview[];
}

export interface UserBookmarksResponse {
  userId: string;
  itineraries: Itinerary[];
}

export type BookSourceType =
  | "public_domain_text_reference"
  | "summary_document"
  | "manually_curated_location_list"
  | "metadata_only";
export type BookIngestionStatus = "pending" | "processing" | "completed" | "failed";
export type CopyrightStatus =
  | "public_domain"
  | "copyrighted"
  | "unknown"
  | "metadata_only";
export type AllowedProcessingMode =
  | "full_text"
  | "summary_only"
  | "metadata_only"
  | "manual_curation";
export type BookLocationCandidateStatus =
  | "candidate"
  | "approved"
  | "promoted"
  | "rejected";

export interface BookSourceCreate {
  sourceType: BookSourceType;
  title?: string | null;
  referenceUrl?: string | null;
  metadata?: Record<string, unknown>;
  sourceLicense?: string | null;
  copyrightStatus?: CopyrightStatus;
  allowedProcessingMode?: AllowedProcessingMode;
  sourceNotes?: string[];
}

export interface BookIngestionJobCreate {
  bookId: string;
  source: BookSourceCreate;
}

export interface BookSource {
  id: string;
  bookId: string;
  sourceType: BookSourceType;
  title?: string | null;
  referenceUrl?: string | null;
  metadata: Record<string, unknown>;
  sourceLicense?: string | null;
  copyrightStatus?: CopyrightStatus;
  allowedProcessingMode?: AllowedProcessingMode;
  sourceNotes?: string[];
  createdAt: string;
}

export interface BookLocationCandidate {
  id: string;
  jobId: string;
  bookId: string;
  destinationId: string;
  name: string;
  description: string;
  latitude: number;
  longitude: number;
  literaryRelevance: string;
  confidence: number;
  status: BookLocationCandidateStatus;
  promotedPoiId?: string | null;
  createdAt: string;
}

export interface BookProcessingArtifact {
  id: string;
  jobId: string;
  artifactType: string;
  payload: Record<string, unknown>;
  providerName?: string | null;
  providerType?: string | null;
  providerVersion?: string | null;
  providerRequestId?: string | null;
  confidenceScore?: number | null;
  provenanceMetadata?: Record<string, unknown>;
  createdAt: string;
}

export interface BookIngestionJob {
  id: string;
  bookId: string;
  source: BookSource;
  status: BookIngestionStatus;
  extractionNotes: string[];
  warnings: string[];
  candidates: BookLocationCandidate[];
  artifacts: BookProcessingArtifact[];
  createdAt: string;
  updatedAt: string;
  completedAt?: string | null;
}

export interface CandidatePromotionResponse {
  candidate: BookLocationCandidate;
  poiId: string;
}

export interface POIVerificationResultResponse {
  status: VerificationStatus;
  provider: string;
  confidence: number;
  verifiedName?: string | null;
  verifiedAddress?: string | null;
  verifiedLatitude?: number | null;
  verifiedLongitude?: number | null;
  openingHoursNote?: string | null;
  ticketingUrl?: string | null;
  notes: string[];
}

export interface CandidateVerificationResponse {
  candidate: BookLocationCandidate;
  verification: POIVerificationResultResponse;
}

export interface POIVerificationResponse {
  poi: POI;
  verification: POIVerificationResultResponse;
}

export interface SeedDataPayload {
  destinations: Destination[];
  books: Book[];
  pois: POI[];
  itineraries: Itinerary[];
}

export interface SeedValidationReport {
  valid: boolean;
  errors: string[];
  warnings: string[];
  counts: Record<string, number>;
}

export interface SeedOperationResult {
  message: string;
  counts: Record<string, number>;
  validation?: SeedValidationReport | null;
}
