# TCS Competitive Intelligence System

A multi-agent system for analyzing AI narratives of TCS competitors using OpenAI's Deep Research API and LangGraph orchestration.

## Overview

This system provides TCS executives with competitive intelligence on AI strategies and narratives from key IT services competitors including Accenture, IBM, Infosys, Cognizant, Capgemini, Wipro, HCLTech, and Deloitte.

## Architecture

- **Deep Research Agent**: Uses OpenAI Deep Research API to gather recent competitive intelligence
- **Synthesizer Agent**: Transforms raw research into executive-ready insights
- **LangGraph Orchestration**: Manages multi-agent workflow and state
- **REST API**: Backend services for frontend integration
- **Minimalist Dashboard**: Executive-focused user interface

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

3. Run the application:
```bash
python -m uvicorn backend.api.main:app --reload
```

## Features

- Automated competitive research (≤2 months old sources)
- Executive report generation
- Real-time progress tracking
- Competitor comparison analysis
- Export capabilities (PDF/PowerPoint)

## Project Structure

```
agentic-researcher/
├── agents/          # Multi-agent implementations
├── backend/         # API and services
├── frontend/        # User interface
├── config/          # Configuration files
├── tests/           # Test suites
└── data/            # Research data storage
```