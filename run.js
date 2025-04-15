#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Get the directory of this script
const scriptDir = path.dirname(__filename);

// Path to the Python script
const pythonScript = path.join(scriptDir, 'mcp_server.py');

// Spawn Python process
const pythonProcess = spawn('python', [pythonScript], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Handle process errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
});

// Handle process exit
pythonProcess.on('exit', (code) => {
  if (code !== 0) {
    console.error(`Python process exited with code ${code}`);
    process.exit(code);
  }
});

// Pipe stdin/stdout
process.stdin.pipe(pythonProcess.stdin);
pythonProcess.stdout.pipe(process.stdout);
pythonProcess.stderr.pipe(process.stderr);

// Handle signals
process.on('SIGINT', () => {
  pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  pythonProcess.kill('SIGTERM');
}); 