// MySQL MCP Server for Smithery
// This file exists to make the package compatible with npm
// The actual server is started by run.js

module.exports = {
  name: "mysql-aqara",
  description: "MySQL MCP server for Smithery",
  isMCPServer: true,
  start: function() {
    require('./run.js');
  }
}; 