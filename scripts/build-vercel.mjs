import { access } from "node:fs/promises";
import { resolve } from "node:path";

const requiredFiles = [
  resolve("docs", "index.html"),
  resolve("docs", "data", "summary.json"),
];

await Promise.all(requiredFiles.map((file) => access(file)));

console.log("Verified static site output in docs");
