# Bank Queue Management System

## Project Overview

The Bank Queue Management System is a real-time resource scheduler designed to optimize the allocation of bank tellers or call center agents to customer requests. The system minimizes customer wait times, maximizes resource utilization, and ensures fair task distribution among agents.

![Bank Queue Management System](https://github.com/yourusername/bank-queue-system/raw/main/screenshots/dashboard.png)

## Features

- **Dynamic Customer Simulation**: Generates customers with randomized service times and priority levels (VIP, Corporate, Normal)
- **Agent Workload Management**: Each agent has configurable workload limits and availability status
- **Multiple Scheduling Algorithms**:
  - Round Robin Scheduling: Distributes tasks equally among agents
  - Priority Scheduling: Prioritizes high-urgency customers (VIP, Corporate)
  - Shortest Job Next: Minimizes delays by prioritizing quicker tasks
- **Real-time Monitoring**: Updates agent availability and workload every 5 seconds
- **Performance Metrics**:
  - Average customer waiting time
  - Agent utilization rates
  - Fairness in task distribution
- **Interactive Dashboard**: Visual representation of system performance

## Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript
- **Threading**: Python's threading module for concurrent processing
- **Containerization**: Docker
- **CI/CD**: GitHub Actions

## Installation and Setup

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bank-queue-system.git
   cd bank-queue-system
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t bank-queue-system .
   ```

2. Run the container:
   ```bash
   docker run -p 5000:5000 bank-queue-system
   ```

3. Access the application at `http://localhost:5000`

## Project Structure

```
bank-queue-system/
├── app.py                 # Main application file
├── Dockerfile             # Docker configuration
├── requirements.txt       # Python dependencies
├── .github/workflows/     # GitHub Actions workflow files
│   └── ci-cd.yml          # CI/CD pipeline configuration
├── tests/                 # Test files
└── README.md              # Project documentation
```

## Usage

### Dashboard

The main dashboard provides a real-time view of:
- Current active scheduling algorithm
- Key performance metrics (wait times, utilization, fairness)
- Agent status and workload
- Customer queue information
- Service history

### Changing Algorithms

Click on the buttons in the Algorithm Selector section to switch between:
- Round Robin
- Priority Scheduling
- Shortest Job Next

### System Components

#### Agent Class
Represents bank tellers or call center agents with properties like:
- Workload limit
- Current workload
- Availability status
- Service history

#### Customer Class
Represents customers with attributes including:
- Priority level
- Service time requirements
- Wait time tracking
- Status updates

## CI/CD Pipeline

The project uses GitHub Actions for Continuous Integration and Deployment:

1. **Automated Testing**: Runs tests on every commit
2. **Docker Build**: Builds and pushes Docker images to Docker Hub
3. **Deployment**: Automatically deploys to cloud platform (e.g., AWS, GitHub Pages)

## Metrics Explained

- **Average Wait Time**: The average time customers spend waiting before being served
- **Agent Utilization**: Percentage of time agents spend handling customers vs. being idle
- **Fairness Score**: Measure of how evenly work is distributed among agents (higher is better)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Team Members

- [Team Member 1](https://github.com/okellobenjamin)
- [Team Member 2](https://github.com/muhweziasaph)
- [Team Member 3](wawirebirali100@gmail.com)

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgements

- [Flask](https://flask.palletsprojects.com/)
- [Docker](https://www.docker.com/)
- [GitHub Actions](https://github.com/features/actions)
