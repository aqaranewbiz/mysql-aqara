#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Get the directory of this script
const scriptDir = __dirname;

// Path to the Python script and virtual environment
const pythonScript = path.join(scriptDir, 'mcp_server.py');
const venvPython = process.platform === 'win32'
    ? path.join(scriptDir, 'venv', 'Scripts', 'python.exe')
    : path.join(scriptDir, 'venv', 'bin', 'python');

// Check if virtual environment exists
if (!fs.existsSync(venvPython)) {
    console.error('Python virtual environment not found. Please run: npm run install');
    process.exit(1);
}

// Spawn Python process using virtual environment
const pythonProcess = spawn(venvPython, [pythonScript], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',  // Ensure Python output is not buffered
        PYTHONIOENCODING: 'utf-8'  // Ensure UTF-8 encoding
    }
});

// Handle stdin/stdout communication
process.stdin.pipe(pythonProcess.stdin);
pythonProcess.stdout.pipe(process.stdout);

// Handle stderr
pythonProcess.stderr.on('data', (data) => {
    console.error(`Python Error: ${data}`);
});

// Handle process termination
pythonProcess.on('close', (code) => {
    if (code !== 0) {
        console.error(`Python process exited with code ${code}`);
        process.exit(code);
    }
});

// Handle errors
pythonProcess.on('error', (err) => {
    console.error('Failed to start Python process:', err);
    process.exit(1);
});

// Handle signals
process.on('SIGINT', () => {
    pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
    pythonProcess.kill('SIGTERM');
}); 