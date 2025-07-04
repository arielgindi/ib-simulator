# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-07

### Added
- Initial release of IB API Simulator
- Complete IB TWS API TCP socket protocol implementation
- Support for multiple concurrent client connections (up to 32)
- DuckDB backend for persistent storage
- Account management with portfolio tracking
- Real-time market data streaming simulation
- Order placement and execution with realistic slippage
- Options trading support with Greeks calculation
- Configuration file support with environment variable overrides
- Network deployment capabilities
- Comprehensive logging system
- Test client for verification
- Full documentation and examples

### Security
- Bcrypt password hashing for test accounts
- Rate limiting to prevent message flooding
- Input validation for all client messages

### Known Limitations
- Historical data generation not yet implemented
- Limited order types (MKT, LMT, STP)
- Options chain generation is simplified
- No market depth (Level 2) data
- Single currency support (USD only)

## [Unreleased]

### Planned Features
- Full options chain generation with term structure
- Additional order types (bracket, trailing stop, etc.)
- Market depth simulation
- Historical data import from real markets
- Multi-currency support
- FIX protocol support
- Web-based monitoring dashboard
- Performance analytics and reports

---

For detailed release notes, see the [GitHub Releases](https://github.com/yourusername/ib-simulator/releases) page.