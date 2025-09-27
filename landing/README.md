
# RAGFlow Landing Page

A modern landing page for RAGFlow with integrated waitlist functionality that connects to the RAGFlow MySQL database.

## Features

- **Modern React Frontend**: Built with Vite, TypeScript, and Tailwind CSS
- **Waitlist Integration**: Collects user information and stores in RAGFlow database
- **Responsive Design**: Mobile-first approach with dark/light theme support
- **Backend API**: Node.js/Express API with MySQL integration
- **Docker Support**: Full containerization for easy deployment
- **CI/CD Ready**: GitHub Actions workflows for automated deployment

## Quick Start

### Frontend Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Full Stack with Database

```bash
# Start all services with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

## Project Structure

```
├── src/                    # React frontend source
│   ├── components/         # React components
│   ├── styles/            # Global styles
│   └── config.ts          # Configuration
├── backend/               # Node.js backend API
│   ├── routes/           # API routes
│   ├── middleware/       # Validation & security
│   ├── config/          # Database configuration
│   └── database/        # SQL schema
├── waitlist.html         # Standalone waitlist page
└── docker-compose.yml    # Full stack deployment
```

## Waitlist Integration

The waitlist form collects user information and stores it in the RAGFlow MySQL database:

- **Frontend**: React component (`src/components/Waitlist.tsx`) and standalone HTML page
- **Backend**: RESTful API with validation and error handling
- **Database**: MySQL table with user information and status tracking

### API Endpoints

- `POST /api/waitlist` - Submit waitlist entry
- `GET /api/waitlist` - Get statistics (admin)
- `GET /health` - Health check

## Deployment

### GitHub Secrets Required

For S3/CloudFront deployment:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET`
- `CLOUDFRONT_DISTRIBUTION_ID` (optional)

For EC2 deployment:
- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_KEY`
- `EC2_TARGET_DIR` (frontend)
- `EC2_BACKEND_DIR` (backend)
- `EC2_POST_DEPLOY_CMD` (optional)

### Environment Variables

Backend configuration (see `backend/env.example`):
```bash
DB_HOST=localhost
DB_PORT=5455
DB_USER=root
DB_PASSWORD=infini_rag_flow
DB_NAME=rag_flow
CORS_ORIGIN=http://localhost:3000
```

## Database Schema

The waitlist table is automatically created:

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
    status ENUM('pending', 'contacted', 'converted') DEFAULT 'pending',
    source VARCHAR(50) DEFAULT 'landing_page'
);
```

## Development

### Frontend
- React 18 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Radix UI components
- React Hook Form for form handling

### Backend
- Node.js with Express
- MySQL2 for database connection
- Joi for validation
- Helmet for security
- Rate limiting

## License

This project is based on the original Figma design and adapted for RAGFlow.