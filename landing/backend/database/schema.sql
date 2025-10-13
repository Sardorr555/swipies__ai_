-- Waitlist table for RAGFlow landing page
CREATE TABLE IF NOT EXISTS waitlist (
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
    source VARCHAR(50) DEFAULT 'landing_page',
    INDEX idx_email (email),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Add some sample data for testing (optional)
-- INSERT INTO waitlist (first_name, last_name, email, company, role, message) VALUES
-- ('John', 'Doe', 'john.doe@example.com', 'Tech Corp', 'CTO', 'Interested in RAGFlow for our AI initiatives');

