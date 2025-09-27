const Joi = require('joi');

// Waitlist form validation schema
const waitlistSchema = Joi.object({
  firstName: Joi.string()
    .min(2)
    .max(100)
    .required()
    .messages({
      'string.min': 'First name must be at least 2 characters long',
      'string.max': 'First name must not exceed 100 characters',
      'any.required': 'First name is required'
    }),
  
  lastName: Joi.string()
    .min(2)
    .max(100)
    .required()
    .messages({
      'string.min': 'Last name must be at least 2 characters long',
      'string.max': 'Last name must not exceed 100 characters',
      'any.required': 'Last name is required'
    }),
  
  email: Joi.string()
    .email()
    .max(255)
    .required()
    .messages({
      'string.email': 'Please provide a valid email address',
      'string.max': 'Email must not exceed 255 characters',
      'any.required': 'Email is required'
    }),
  
  phone: Joi.string()
    .pattern(/^[\+]?[1-9][\d]{0,15}$/)
    .optional()
    .allow('')
    .messages({
      'string.pattern.base': 'Please provide a valid phone number'
    }),
  
  company: Joi.string()
    .max(255)
    .optional()
    .allow('')
    .messages({
      'string.max': 'Company name must not exceed 255 characters'
    }),
  
  role: Joi.string()
    .max(100)
    .optional()
    .allow('')
    .messages({
      'string.max': 'Role must not exceed 100 characters'
    }),
  
  message: Joi.string()
    .max(1000)
    .optional()
    .allow('')
    .messages({
      'string.max': 'Message must not exceed 1000 characters'
    })
});

// Validation middleware
const validateWaitlist = (req, res, next) => {
  const { error, value } = waitlistSchema.validate(req.body, {
    abortEarly: false,
    stripUnknown: true
  });

  if (error) {
    const errors = error.details.map(detail => ({
      field: detail.path[0],
      message: detail.message
    }));

    return res.status(400).json({
      success: false,
      message: 'Validation failed',
      errors
    });
  }

  req.validatedData = value;
  next();
};

module.exports = {
  validateWaitlist
};
