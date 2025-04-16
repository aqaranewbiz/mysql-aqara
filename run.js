#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

// Get the directory of this script
const scriptDir = path.dirname(__filename);

// Path to the Python script
const pythonScript = path.join(scriptDir, 'mcp_server.py');

console.error('Starting MySQL MCP server...');
console.error(`Python script path: ${pythonScript}`);

// Determine Python executable
const pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';

// Spawn Python process with unbuffered output
const pythonProcess = spawn(pythonExecutable, ['-u', pythonScript], {
  stdio: ['pipe', 'pipe', 'pipe'],
  env: {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    PYTHONIOENCODING: 'utf-8'
  }
});

console.error(`Started Python process with PID: ${pythonProcess.pid}`);

// Set up buffers for line processing
let stdoutBuffer = '';
let stderrBuffer = '';

// Handle process errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
});

// Handle process exit
pythonProcess.on('exit', (code, signal) => {
  if (signal) {
    console.error(`Python process was killed with signal: ${signal}`);
    process.exit(1);
  }
  
  if (code !== 0) {
    console.error(`Python process exited with code ${code}`);
    process.exit(code);
  }
  
  console.error('Python process exited normally');
});

// Process stdout line by line
pythonProcess.stdout.on('data', (data) => {
  stdoutBuffer += data.toString();
  
  let newlineIndex;
  while ((newlineIndex = stdoutBuffer.indexOf('\n')) !== -1) {
    const line = stdoutBuffer.substring(0, newlineIndex);
    stdoutBuffer = stdoutBuffer.substring(newlineIndex + 1);
    
    // Output to process.stdout
    process.stdout.write(line + '\n');
  }
});

// Process stderr for logging
pythonProcess.stderr.on('data', (data) => {
  stderrBuffer += data.toString();
  
  let newlineIndex;
  while ((newlineIndex = stderrBuffer.indexOf('\n')) !== -1) {
    const line = stderrBuffer.substring(0, newlineIndex);
    stderrBuffer = stderrBuffer.substring(newlineIndex + 1);
    
    // Output to process.stderr
    console.error(`[Python] ${line}`);
  }
});

// Process stdin for input
process.stdin.on('data', (data) => {
  try {
    pythonProcess.stdin.write(data);
  } catch (err) {
    console.error('Error writing to Python process:', err);
  }
});

// Handle process closing
process.stdin.on('end', () => {
  try {
    pythonProcess.stdin.end();
  } catch (err) {
    console.error('Error ending Python stdin:', err);
  }
});

// Handle signals
process.on('SIGINT', () => {
  console.error('Received SIGINT, terminating Python process...');
  pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  console.error('Received SIGTERM, terminating Python process...');
  pythonProcess.kill('SIGTERM');
}); 