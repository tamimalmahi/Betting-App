const adminRoutes = require('./routes/adminRoutes');

app.use(express.json()); // must আছে
app.use('/api/admin', adminRoutes);

const transactionRoutes = require('./routes/transactionRoutes');

app.use('/api', transactionRoutes);
