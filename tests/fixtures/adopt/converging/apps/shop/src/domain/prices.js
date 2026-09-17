// The domain: what a basket costs. Imports nothing, so the import gate has nothing to say about it.
exports.total = (items) => items.reduce((sum, item) => sum + item.price, 0);
