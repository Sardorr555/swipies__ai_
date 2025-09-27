# RAGFlow Landing Backend

Backend API for the RAGFlow landing page waitlist functionality.

## Features

- RESTful API for waitlist submissions
- MySQL database integration with RAGFlow
- Input validation and error handling
- Rate limiting and security headers
- Health check endpoint
- Statistics endpoint for admin use

## Environment Variables

Copy `env.example` to `.env` and configure:

```bash
# Database Configuration (RAGFlow MySQL)
DB_HOST=localhost
DB_PORT=5455
DB_USER=root
DB_PASSWORD=infini_rag_flow
DB_NAME=rag_flow

# Server Configuration
PORT=3001
NODE_ENV=development

# CORS Configuration
CORS_ORIGIN=http://localhost:3000

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=10
```

## Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Start production server
npm start
```

## API Endpoints

### POST /api/waitlist
Submit a new waitlist entry.

**Request Body:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "company": "Tech Corp",
  "role": "CTO",
  "message": "Interested in RAGFlow"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully added to waitlist",
  "data": {
    "id": 1,
    "email": "john@example.com"
  }
}
```

### GET /api/waitlist
Get waitlist statistics (admin use).

**Response:**
```json
{
  "success": true,
  "data": {
    "total": 150,
    "byStatus": {
      "pending": 120,
      "contacted": 25,
      "converted": 5
    },
    "recent": 10
  }
}
```

### GET /api/waitlist/:id
Get specific waitlist entry by ID.

### GET /health
Health check endpoint.

## Database Schema

The waitlist table is automatically created with the following structure:

```sql
CREATE TABLE waitlist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20),
    company VARCHAR(255),
    role VARCHAR(100),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status ENUM('pending', 'contacted', 'converted') DEFAULT 'pending',
    source VARCHAR(50) DEFAULT 'landing_page'
);
```

## Deployment

### Docker

```bash
# Build image
docker build -t ragflow-backend .

# Run container
docker run -p 3001:3001 --env-file .env ragflow-backend
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### EC2 Deployment

1. Copy the backend files to your EC2 instance
2. Install Node.js and dependencies
3. Copy the systemd service file:
   ```bash
   sudo cp ragflow-backend.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable ragflow-backend
   sudo systemctl start ragflow-backend
   ```

## Security

- Rate limiting (10 requests per 15 minutes by default)
- Input validation using Joi
- SQL injection protection with parameterized queries
- CORS configuration
- Security headers via Helmet
- Non-root user in Docker container

## Monitoring

- Health check endpoint at `/health`
- Structured logging
- Error tracking and reporting
- Database connection monitoring
