// A service: `npm start` runs it, which is what tells the survey what this directory is for.
exports.total = (lines) => lines.reduce((sum, line) => sum + line.price * line.quantity, 0);
if (require.main === module) {
  console.log("orders listening");
}
