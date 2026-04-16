const express = require('express');
const router = express.Router();
const {
  depositRequest,
  withdrawRequest
} = require('../controllers/transactionController');

const auth = require('../middleware/auth');

router.post('/deposit', auth, depositRequest);
router.post('/withdraw', auth, withdrawRequest);

module.exports = router;
