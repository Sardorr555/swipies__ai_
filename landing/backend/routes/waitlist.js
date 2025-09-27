const express = require('express');
const { pool } = require('../config/database');
const { validateWaitlist } = require('../middleware/validation');

const router = express.Router();

// POST /api/waitlist - Add user to waitlist
router.post('/', validateWaitlist, async (req, res) => {
  const connection = await pool.getConnection();
  
  try {
    const {
      firstName,
      lastName,
      email,
      phone,
      company,
      role,
      message
    } = req.validatedData;

    // Check if email already exists
    const [existingUsers] = await connection.execute(
      'SELECT id FROM waitlist WHERE email = ?',
      [email]
    );

    if (existingUsers.length > 0) {
      return res.status(409).json({
        success: false,
        message: 'Email already registered in waitlist'
      });
    }

    // Insert new waitlist entry
    const [result] = await connection.execute(
      `INSERT INTO waitlist 
       (first_name, last_name, email, phone, company, role, message, source) 
       VALUES (?, ?, ?, ?, ?, ?, ?, 'landing_page')`,
      [firstName, lastName, email, phone || null, company || null, role || null, message || null]
    );

    res.status(201).json({
      success: true,
      message: 'Successfully added to waitlist',
      data: {
        id: result.insertId,
        email: email
      }
    });

  } catch (error) {
    console.error('Waitlist submission error:', error);
    
    res.status(500).json({
      success: false,
      message: 'Internal server error',
      error: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
    });
  } finally {
    connection.release();
  }
});

// GET /api/waitlist - Get waitlist statistics (admin only)
router.get('/', async (req, res) => {
  const connection = await pool.getConnection();
  
  try {
    // Get total count
    const [totalResult] = await connection.execute(
      'SELECT COUNT(*) as total FROM waitlist'
    );
    
    // Get count by status
    const [statusResult] = await connection.execute(
      'SELECT status, COUNT(*) as count FROM waitlist GROUP BY status'
    );
    
    // Get recent signups (last 7 days)
    const [recentResult] = await connection.execute(
      'SELECT COUNT(*) as recent FROM waitlist WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)'
    );

    res.json({
      success: true,
      data: {
        total: totalResult[0].total,
        byStatus: statusResult.reduce((acc, row) => {
          acc[row.status] = row.count;
          return acc;
        }, {}),
        recent: recentResult[0].recent
      }
    });

  } catch (error) {
    console.error('Waitlist stats error:', error);
    
    res.status(500).json({
      success: false,
      message: 'Internal server error',
      error: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
    });
  } finally {
    connection.release();
  }
});

// GET /api/waitlist/:id - Get specific waitlist entry (admin only)
router.get('/:id', async (req, res) => {
  const connection = await pool.getConnection();
  
  try {
    const { id } = req.params;
    
    const [rows] = await connection.execute(
      'SELECT * FROM waitlist WHERE id = ?',
      [id]
    );

    if (rows.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'Waitlist entry not found'
      });
    }

    res.json({
      success: true,
      data: rows[0]
    });

  } catch (error) {
    console.error('Waitlist fetch error:', error);
    
    res.status(500).json({
      success: false,
      message: 'Internal server error',
      error: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
    });
  } finally {
    connection.release();
  }
});

module.exports = router;
