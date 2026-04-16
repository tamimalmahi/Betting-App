const Transaction = require('../models/Transaction');

exports.depositRequest = async (req, res) => {
  try {
    const { amount } = req.body;

    const newDeposit = new Transaction({
      userId: req.user.id,
      amount,
      type: "deposit",
      status: "pending"
    });

    await newDeposit.save();

    res.json({ msg: "Deposit request sent" });

  } catch (err) {
    res.status(500).json({ msg: "Server error" });
  }
};

exports.withdrawRequest = async (req, res) => {
  try {
    const { amount } = req.body;

    const newWithdraw = new Transaction({
      userId: req.user.id,
      amount,
      type: "withdraw",
      status: "pending"
    });

    await newWithdraw.save();

    res.json({ msg: "Withdraw request sent" });

  } catch (err) {
    res.status(500).json({ msg: "Server error" });
  }
};
