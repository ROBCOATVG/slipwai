// TODO: currencies other than GBP
exports.total = (lines) => lines.reduce((sum, line) => sum + line.price * line.quantity, 0);
