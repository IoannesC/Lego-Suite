import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const baseDir = path.resolve(__dirname, '..');
const targetDir = path.join(baseDir, 'defaults', 'i18n');
const outputFile = path.join(baseDir, 'src', 'i18n', 'languages.json');

if (!fs.existsSync(targetDir)) {
  console.error(`Error: Directory ${targetDir} not found.`);
  process.exit(1);
}

const result = {};
for (const file of fs.readdirSync(targetDir).sort()) {
  if (!file.endsWith('.json')) continue;
  const key = file.slice(0, -5);
  result[key] = JSON.parse(fs.readFileSync(path.join(targetDir, file), 'utf8'));
}

fs.writeFileSync(outputFile, JSON.stringify(result, null, 2) + '\n');
