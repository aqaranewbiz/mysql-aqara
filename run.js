#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Get the directory of this script
const scriptDir = __dirname;

// Path to the Python script
const pythonScript = path.join(scriptDir, 'mcp_server.py');

// Spawn the Python process
const pythonProcess = spawn('python', [pythonScript], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Handle stdin/stdout communication
process.stdin.pipe(pythonProcess.stdin);
pythonProcess.stdout.pipe(process.stdout);
pythonProcess.stderr.pipe(process.stderr);

// Handle process termination
pythonProcess.on('close', (code) => {
  process.exit(code);
});

// Handle errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
}); 