/**
 * Shared Types Module
 * Tipos compartidos entre todos los módulos de la aplicación
 */

// Base Entity Interface
export interface BaseEntity {
  id: string;
  createdAt: Date;
  updatedAt: Date;
}

// Institution Entity
export interface Institution extends BaseEntity {
  name: string;
  code: string;
  latitude: number;
  longitude: number;
  address: string;
  phone?: string;
  email?: string;
  website?: string;
  type: InstitutionType;
  level: EducationLevel;
  status: InstitutionStatus;
  studentsCount: number;
  teachersCount: number;
  classroomsCount: number;
  lastInspectionDate?: Date;
  director?: string;
  municipality: string;
  department: string;
  zone: 'urban' | 'rural';
  infrastructure?: InfrastructureData;
  academicData?: AcademicData;
}

// Institution Types
export type InstitutionType = 
  | 'public' 
  | 'private' 
  | 'cooperative' 
  | 'technical' 
  | 'religious';

export type EducationLevel = 
  | 'preschool' 
  | 'primary' 
  | 'secondary' 
  | 'technical' 
  | 'university' 
  | 'mixed';

export type InstitutionStatus = 
  | 'active' 
  | 'inactive' 
  | 'suspended' 
  | 'under_review';

// Infrastructure Data
export interface InfrastructureData {
  hasLibrary: boolean;
  hasLaboratory: boolean;
  hasComputerRoom: boolean;
  hasSportsField: boolean;
  hasCafeteria: boolean;
  hasInternet: boolean;
  waterAccess: 'potable' | 'well' | 'none';
  electricityAccess: boolean;
  buildingCondition: 'excellent' | 'good' | 'regular' | 'poor';
}

// Academic Data
export interface AcademicData {
  approvalRate: number;
  dropoutRate: number;
  repetitionRate: number;
  graduationRate?: number;
  averageScore?: number;
  testResults?: TestResult[];
}

export interface TestResult {
  testName: string;
  year: number;
  score: number;
  level: 'low' | 'basic' | 'satisfactory' | 'advanced';
}

// Filter Options
export interface FilterOptions {
  type?: InstitutionType[];
  level?: EducationLevel[];
  status?: InstitutionStatus[];
  municipality?: string[];
  department?: string[];
  zone?: ('urban' | 'rural')[];
  minStudents?: number;
  maxStudents?: number;
  hasInternet?: boolean;
  hasLibrary?: boolean;
  buildingCondition?: ('excellent' | 'good' | 'regular' | 'poor')[];
}

// Search Options
export interface SearchOptions {
  query: string;
  fields?: ('name' | 'code' | 'municipality' | 'director')[];
  fuzzy?: boolean;
}

// Pagination
export interface PaginationOptions {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
  message?: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: any;
}

// Geographic Types
export interface GeographicBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface MapCenter {
  lat: number;
  lng: number;
  zoom: number;
}

// Event Types
export interface AppEvent<T = any> {
  type: string;
  payload: T;
  timestamp: Date;
  source: string;
}

// Map-specific Types
export interface MapTool {
  id: string;
  name: string;
  tooltip: string;
  active: boolean;
}

export interface Coordinates {
  lat: number;
  lng: number;
}

export interface MapViewState {
  center: Coordinates;
  zoom: number;
  bounds?: GeographicBounds;
}

export interface SearchResult {
  institution: Institution;
  relevance: number;
  distance?: number;
}
