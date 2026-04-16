const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const User = require('../models/User');

exports.adminLogin = async (req, res) => {
  try {
    const { email, password } = req.body;

    // user check
    const user = await User.findOne({ email });
    if (!user) {
      return res.status(400).json({ msg: "Admin not found" });
    }

    // role check
    if (user.role !== 'admin') {
      return res.status(403).json({ msg: "Access denied. Not admin." });
    }

    // password check
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(400).json({ msg: "Wrong password" });
    }

    // token
    const token = jwt.sign(
      { id: user._id, role: user.role },
      "SECRETKEY",
      { expiresIn: "7d" }
    );

    res.json({
      token,
      user: {
        id: user._id,
        email: user.email,
        role: user.role
      }
    });

  } catch (err) {
    console.log(err);
    res.status(500).json({ msg: "Server error" });
  }
};
