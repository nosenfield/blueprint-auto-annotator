# System Patterns: Room Boundary Detection System

**Last Updated**: 2025-11-09

## Coding Standards

### Python Backend Standards

#### File Organization
```python
# Standard module structure
"""
Module docstring describing purpose
"""
import standard_library  # Standard library imports first
import third_party       # Third-party imports second
from .local import foo   # Local imports last

# Constants
CONSTANT_NAME = value

# Classes
class ClassName:
    """Class docstring"""
    pass

# Functions
def function_name() -> ReturnType:
    """Function docstring"""
    pass
```

#### Type Hints (Required)
```python
# Always use type hints for function signatures
def process_walls(
    walls: List[Wall],
    width: int,
    height: int
) -> List[Room]:
    """
    Convert wall detections to room polygons.

    Args:
        walls: List of detected wall objects
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        List of detected room objects
    """
    pass

# Use Pydantic for data validation
from pydantic import BaseModel, Field

class Wall(BaseModel):
    id: str
    bounding_box: Tuple[int, int, int, int]
    confidence: float = Field(..., ge=0.0, le=1.0)
```

#### Naming Conventions
```python
# Classes: PascalCase
class GeometricRoomDetector:
    pass

# Functions/Variables: snake_case
def detect_rooms(image_data: bytes) -> RoomDetectionResponse:
    wall_count = 0
    processing_time = 0.0

# Constants: UPPER_SNAKE_CASE
MAX_IMAGE_SIZE = 10_000_000
DEFAULT_CONFIDENCE = 0.10

# Private: Leading underscore
def _internal_helper() -> None:
    pass
```

#### Error Handling
```python
# Use specific exceptions
from fastapi import HTTPException

# Bad
try:
    result = process()
except:
    pass

# Good
try:
    result = process_walls(walls)
except ValidationError as e:
    raise HTTPException(
        status_code=400,
        detail={"error": "VALIDATION_ERROR", "message": str(e)}
    )
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
    raise HTTPException(
        status_code=500,
        detail={"error": "PROCESSING_ERROR", "message": "Failed to detect rooms"}
    )
```

### TypeScript Frontend Standards

#### File Organization
```typescript
// Imports
import React from 'react';  // External libraries
import { api } from '../services/api';  // Local imports

// Types/Interfaces
interface ComponentProps {
  data: DataType;
  onUpdate: (value: string) => void;
}

// Component
export const ComponentName: React.FC<ComponentProps> = ({ data, onUpdate }) => {
  // Hooks
  const [state, setState] = useState<StateType>(initialValue);

  // Event handlers
  const handleClick = () => {
    // handler logic
  };

  // Render
  return (
    <div>Content</div>
  );
};
```

#### Naming Conventions
```typescript
// Components: PascalCase
const FileUpload: React.FC = () => {};

// Functions/Variables: camelCase
const handleFileSelected = (file: File) => {};
const processingState = { status: 'idle' };

// Types/Interfaces: PascalCase
interface RoomDetectionResponse {
  success: boolean;
  rooms: Room[];
}

// Constants: UPPER_SNAKE_CASE
const MAX_FILE_SIZE = 10_000_000;
const API_TIMEOUT = 30_000;

// CSS classes: kebab-case (Tailwind)
<div className="flex items-center justify-between">
```

#### Type Safety
```typescript
// Always define types
interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
}

// Use generics
function processResponse<T>(response: ApiResponse<T>): T | null {
  return response.success ? response.data : null;
}

// Avoid 'any'
// Bad
const data: any = fetchData();

// Good
interface FetchedData {
  id: string;
  value: number;
}
const data: FetchedData = await fetchData();
```

---

## API Design Patterns

### RESTful Endpoints
```yaml
Pattern: /api/{resource-action}

Endpoints:
  POST /api/detect-walls
    - Purpose: Detect walls in blueprint
    - Input: { image, confidence_threshold }
    - Output: { walls, image_dimensions }

  POST /api/detect-rooms
    - Purpose: Convert walls to rooms
    - Input: { walls, image_dimensions }
    - Output: { rooms, visualization }

Future:
  POST /api/detect-all
    - Combined endpoint for single-request processing
```

### Request/Response Pattern
```python
# Standard response structure
class BaseResponse(BaseModel):
    success: bool
    processing_time_ms: float

class SuccessResponse(BaseResponse):
    success: Literal[True]
    # ... data fields

class ErrorResponse(BaseResponse):
    success: Literal[False]
    error: dict

# Always return consistent structure
@app.post("/api/endpoint")
async def endpoint() -> Union[SuccessResponse, ErrorResponse]:
    try:
        result = process()
        return SuccessResponse(
            success=True,
            processing_time_ms=time_ms,
            **result
        )
    except Exception as e:
        return ErrorResponse(
            success=False,
            processing_time_ms=0,
            error={"code": "ERROR_CODE", "message": str(e)}
        )
```

### Pagination Pattern (Future)
```python
class PaginatedResponse(BaseModel):
    success: bool
    data: List[Any]
    pagination: dict = {
        "page": 1,
        "per_page": 20,
        "total": 100,
        "total_pages": 5
    }
```

---

## State Management Patterns

### React State Pattern
```typescript
// Use useState for component-local state
const [state, setState] = useState<StateType>(initialValue);

// Use useReducer for complex state
type Action =
  | { type: 'START_PROCESSING' }
  | { type: 'UPDATE_PROGRESS'; payload: number }
  | { type: 'COMPLETE'; payload: Results };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'START_PROCESSING':
      return { ...state, status: 'processing', progress: 0 };
    case 'UPDATE_PROGRESS':
      return { ...state, progress: action.payload };
    case 'COMPLETE':
      return { ...state, status: 'complete', results: action.payload };
    default:
      return state;
  }
}

const [state, dispatch] = useReducer(reducer, initialState);
```

### Context Pattern (Future)
```typescript
// For shared state across components
interface AppContextType {
  user: User | null;
  settings: Settings;
  updateSettings: (settings: Partial<Settings>) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [settings, setSettings] = useState<Settings>(defaultSettings);

  return (
    <AppContext.Provider value={{ user, settings, updateSettings: setSettings }}>
      {children}
    </AppContext.Provider>
  );
};
```

---

## Testing Patterns

### Backend Unit Tests
```python
# test_geometric.py
import pytest
from app.geometric import GeometricRoomDetector
from app.models import Wall

def test_detect_rooms_simple_rectangle():
    """Test detection of simple rectangular room"""
    detector = GeometricRoomDetector(min_room_area=1000)
    walls = [
        Wall(id="wall_1", bounding_box=[0, 0, 5, 100], confidence=0.9),
        Wall(id="wall_2", bounding_box=[95, 0, 100, 100], confidence=0.9),
        Wall(id="wall_3", bounding_box=[0, 0, 100, 5], confidence=0.9),
        Wall(id="wall_4", bounding_box=[0, 95, 100, 100], confidence=0.9),
    ]

    rooms = detector.detect_rooms(walls, width=100, height=100)

    assert len(rooms) == 1
    assert rooms[0].shape_type == "rectangle"
    assert rooms[0].area_pixels > 8000  # Approximate inner area

@pytest.fixture
def sample_walls():
    """Fixture for reusable test data"""
    return [
        Wall(id=f"wall_{i}", bounding_box=[x1, y1, x2, y2], confidence=0.85)
        for i in range(10)
    ]
```

### Frontend Component Tests
```typescript
// FileUpload.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { FileUpload } from './FileUpload';

describe('FileUpload', () => {
  it('renders upload area', () => {
    const onFileSelected = jest.fn();
    render(<FileUpload onFileSelected={onFileSelected} />);

    expect(screen.getByText(/drop your blueprint/i)).toBeInTheDocument();
  });

  it('calls onFileSelected when file is dropped', async () => {
    const onFileSelected = jest.fn();
    render(<FileUpload onFileSelected={onFileSelected} />);

    const file = new File(['content'], 'blueprint.png', { type: 'image/png' });
    const input = screen.getByRole('button');

    fireEvent.drop(input, { dataTransfer: { files: [file] } });

    expect(onFileSelected).toHaveBeenCalledWith(file);
  });
});
```

---

## Error Handling Patterns

### Backend Error Hierarchy
```python
class AppError(Exception):
    """Base application error"""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)

class ValidationError(AppError):
    """Input validation error"""
    pass

class ProcessingError(AppError):
    """Data processing error"""
    pass

class ResourceError(AppError):
    """Resource not found or unavailable"""
    pass

# Usage
if len(walls) == 0:
    raise ValidationError("No walls provided", "NO_WALLS")

if not detect_success:
    raise ProcessingError("Room detection failed", "DETECTION_FAILED")
```

### Frontend Error Handling
```typescript
// Error boundary for React
class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback />;
    }
    return this.props.children;
  }
}

// API error handling
try {
  const response = await api.detectWalls(file);
  handleSuccess(response);
} catch (error) {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 400) {
      handleValidationError(error.response.data);
    } else if (error.response?.status === 500) {
      handleServerError(error.response.data);
    } else {
      handleNetworkError();
    }
  } else {
    handleUnknownError(error);
  }
}
```

---

## Logging Patterns

### Structured Logging
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log(self, level: str, message: str, **kwargs):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logger.log(
            getattr(logging, level.upper()),
            json.dumps(log_entry)
        )

# Usage
logger = StructuredLogger(__name__)
logger.log(
    "info",
    "Processing request",
    request_id="abc-123",
    walls_count=34,
    processing_time_ms=1250
)
```

### Frontend Logging
```typescript
// Development logging
if (process.env.NODE_ENV === 'development') {
  console.log('API Response:', response);
}

// Production error tracking (future)
class ErrorTracker {
  static logError(error: Error, context?: Record<string, any>) {
    // Send to error tracking service (Sentry, etc.)
    console.error('Error:', error, 'Context:', context);
  }
}
```

---

## Performance Patterns

### Lazy Loading
```typescript
// Code splitting for routes (future)
const Results = lazy(() => import('./components/Results'));

<Suspense fallback={<Loading />}>
  <Results />
</Suspense>
```

### Memoization
```typescript
// Memoize expensive computations
const expensiveValue = useMemo(() => {
  return calculateExpensiveValue(data);
}, [data]);

// Memoize callbacks
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);
```

### Backend Optimization
```python
# Cache YOLO model at module level (Lambda optimization)
_model_cache = None

def get_model():
    global _model_cache
    if _model_cache is None:
        _model_cache = YOLO("models/yolov8l.pt")
    return _model_cache

# Use generators for memory efficiency
def process_large_dataset(data: List[Any]) -> Iterator[Result]:
    for item in data:
        yield process_item(item)
```

---

## Security Patterns

### Input Validation
```python
# Always validate with Pydantic
class WallDetectionRequest(BaseModel):
    image: str = Field(..., min_length=100)  # Ensure not empty
    confidence_threshold: float = Field(0.10, ge=0.0, le=1.0)
    image_format: str = Field("png", regex="^(png|jpg|jpeg)$")

    @validator('image')
    def validate_base64(cls, v):
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError('Invalid base64 encoding')
```

### CORS Configuration
```python
# Production CORS (restrictive)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Development CORS (permissive)
if os.getenv("ENV") == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

### Rate Limiting (Future)
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/api/detect-walls", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def detect_walls():
    pass
```

---

## Documentation Patterns

### Code Documentation
```python
def detect_rooms(
    walls: List[Wall],
    width: int,
    height: int
) -> List[Room]:
    """
    Convert wall detections to room boundary polygons.

    This function uses a geometric algorithm based on connected component
    analysis to identify enclosed spaces (rooms) from detected wall segments.

    Algorithm:
        1. Create binary grid from image dimensions
        2. Draw walls as filled rectangles
        3. Invert grid (walls=black, rooms=white)
        4. Apply morphological operations to clean up
        5. Find connected components
        6. Extract and simplify contours
        7. Filter by minimum area

    Args:
        walls: List of detected wall objects with bounding boxes
        width: Blueprint image width in pixels
        height: Blueprint image height in pixels

    Returns:
        List of Room objects with polygon vertices and metadata

    Raises:
        ValidationError: If walls list is empty or dimensions invalid
        ProcessingError: If room detection algorithm fails

    Example:
        >>> walls = [Wall(id="w1", bounding_box=[0,0,10,100], confidence=0.9)]
        >>> rooms = detect_rooms(walls, width=800, height=600)
        >>> len(rooms)
        5
    """
    pass
```

### API Documentation
```python
# FastAPI auto-generates OpenAPI docs
@app.post(
    "/api/detect-rooms",
    response_model=RoomDetectionResponse,
    summary="Detect room boundaries from walls",
    description="""
    Analyzes wall detections and identifies enclosed room spaces using
    geometric algorithms. Returns room polygons and optional visualization.
    """,
    responses={
        200: {"description": "Successfully detected rooms"},
        400: {"description": "Invalid input data"},
        500: {"description": "Processing error"}
    }
)
async def detect_rooms(request: RoomDetectionRequest):
    pass
```

---

## Common Patterns Reference

### Singleton Pattern
```python
class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.config = load_config()
        self._initialized = True
```

### Factory Pattern
```python
class DetectorFactory:
    @staticmethod
    def create(detector_type: str) -> BaseDetector:
        if detector_type == "yolo":
            return YOLODetector()
        elif detector_type == "geometric":
            return GeometricDetector()
        else:
            raise ValueError(f"Unknown detector type: {detector_type}")
```

### Observer Pattern (React)
```typescript
// Custom hook for observable state
function useObservable<T>(observable: Observable<T>) {
  const [state, setState] = useState<T>();

  useEffect(() => {
    const subscription = observable.subscribe(setState);
    return () => subscription.unsubscribe();
  }, [observable]);

  return state;
}
```

---

## Best Practices Checklist

### Before Committing Code
- [ ] All functions have type hints (Python) / types (TypeScript)
- [ ] All public functions have docstrings
- [ ] No commented-out code
- [ ] No debug print statements
- [ ] Error handling implemented
- [ ] Tests written and passing
- [ ] No hardcoded credentials or secrets
- [ ] Code follows naming conventions
- [ ] Imports organized correctly
- [ ] No unused variables or imports

### Before Deploying
- [ ] Environment variables configured
- [ ] Error tracking enabled
- [ ] Logging configured
- [ ] Performance tested
- [ ] Security reviewed
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Tests passing in CI/CD
