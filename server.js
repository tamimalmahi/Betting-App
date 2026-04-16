const adminRoutes = require('./routes/adminRoutes');

app.use(express.json()); // must আছে
app.use('/api/admin', adminRoutes);
