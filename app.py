import time
import random
import threading
import queue
from flask import Flask, render_template_string, jsonify
import uuid
from datetime import datetime, timedelta

# Initialize Flask app
app = Flask(__name__)

# Constants
PRIORITY_LEVELS = {
    "VIP": 3,
    "Corporate": 2,
    "Normal": 1
}

# Global variables
agents = []
customers = []
waiting_queue = []
service_history = []
agent_lock = threading.Lock()
customer_lock = threading.Lock()
queue_lock = threading.Lock()
history_lock = threading.Lock()

class Agent:
    def __init__(self, agent_id, name, workload_limit):
        self.agent_id = agent_id
        self.name = name
        self.workload_limit = workload_limit
        self.current_workload = 0
        self.available = True
        self.customers_served = []
        self.total_service_time = 0
        self.idle_time = 0
        self.last_status_change = datetime.now()

    def assign_customer(self, customer):
        if self.current_workload < self.workload_limit:
            self.current_workload += 1
            if self.current_workload == self.workload_limit:
                self.available = False
            self.customers_served.append(customer)
            customer.status = "Being Served"
            customer.assigned_agent = self.agent_id
            customer.service_start_time = datetime.now()
            return True
        return False

    def complete_service(self, customer):
        self.current_workload -= 1
        if self.current_workload < self.workload_limit:
            self.available = True
        service_duration = (datetime.now() - customer.service_start_time).total_seconds()
        self.total_service_time += service_duration
        customer.status = "Completed"
        customer.service_end_time = datetime.now()
        customer.wait_time = (customer.service_start_time - customer.arrival_time).total_seconds()
        return service_duration

    def update_status(self):
        now = datetime.now()
        if not self.available:
            self.last_status_change = now
        else:
            self.idle_time += (now - self.last_status_change).total_seconds()
            self.last_status_change = now

    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "workload_limit": self.workload_limit,
            "current_workload": self.current_workload,
            "available": self.available,
            "customers_served": len(self.customers_served),
            "utilization_rate": self.calculate_utilization_rate(),
        }

    def calculate_utilization_rate(self):
        total_time = (datetime.now() - self.last_status_change).total_seconds() + self.total_service_time + self.idle_time
        if total_time > 0:
            return round((self.total_service_time / total_time) * 100, 2)
        return 0

class Customer:
    def __init__(self, customer_id, priority, service_time):
        self.customer_id = customer_id
        self.priority = priority
        self.priority_level = PRIORITY_LEVELS[priority]
        self.service_time = service_time  # in seconds
        self.arrival_time = datetime.now()
        self.service_start_time = None
        self.service_end_time = None
        self.status = "Waiting"
        self.assigned_agent = None
        self.wait_time = None

    def to_dict(self):
        return {
            "customer_id": self.customer_id,
            "priority": self.priority,
            "service_time": self.service_time,
            "arrival_time": self.arrival_time.strftime("%H:%M:%S"),
            "status": self.status,
            "assigned_agent": self.assigned_agent,
            "wait_time": self.wait_time if self.wait_time is not None else "N/A"
        }

# Scheduling algorithms
def round_robin_scheduling():
    with queue_lock:
        if not waiting_queue:
            return None
    
    with agent_lock:
        available_agents = [agent for agent in agents if agent.available]
        if not available_agents:
            return None
            
        agent = available_agents[0]  # Get the first available agent
        
        with queue_lock:
            customer = waiting_queue.pop(0)
            
        agent.assign_customer(customer)
        return customer

def priority_scheduling():
    with queue_lock:
        if not waiting_queue:
            return None
            
        # Sort by priority (highest first)
        waiting_queue.sort(key=lambda c: (-c.priority_level, c.arrival_time))
        
    with agent_lock:
        available_agents = [agent for agent in agents if agent.available]
        if not available_agents:
            return None
            
        agent = max(available_agents, key=lambda a: a.workload_limit - a.current_workload)
        
        with queue_lock:
            customer = waiting_queue.pop(0)
            
        agent.assign_customer(customer)
        return customer

def shortest_job_next():
    with queue_lock:
        if not waiting_queue:
            return None
            
        # Sort by service time (shortest first)
        waiting_queue.sort(key=lambda c: (c.service_time, -c.priority_level))
        
    with agent_lock:
        available_agents = [agent for agent in agents if agent.available]
        if not available_agents:
            return None
            
        agent = min(available_agents, key=lambda a: a.current_workload)
        
        with queue_lock:
            customer = waiting_queue.pop(0)
            
        agent.assign_customer(customer)
        return customer

# Active scheduling algorithm
current_algorithm = round_robin_scheduling

def customer_generator():
    """Simulate customer arrivals"""
    while True:
        # Generate a new customer every 1-5 seconds
        time.sleep(random.uniform(1, 5))
        
        # Randomize customer properties
        priority = random.choices(["Normal", "Corporate", "VIP"], weights=[0.7, 0.2, 0.1])[0]
        service_time = random.randint(5, 30)  # Service time in seconds
        
        customer = Customer(str(uuid.uuid4())[:8], priority, service_time)
        
        with customer_lock:
            customers.append(customer)
            
        with queue_lock:
            waiting_queue.append(customer)
            
        print(f"New customer arrived: {customer.customer_id}, Priority: {customer.priority}, Service Time: {customer.service_time}s")

def service_processor():
    """Process customer service"""
    while True:
        # Try to assign customers to agents
        assigned_customer = current_algorithm()
        
        if assigned_customer:
            print(f"Customer {assigned_customer.customer_id} assigned to agent with ID {assigned_customer.assigned_agent}")
            
            # Simulate service time
            time.sleep(assigned_customer.service_time)
            
            # Complete service
            with agent_lock:
                serving_agent = next((a for a in agents if a.agent_id == assigned_customer.assigned_agent), None)
                if serving_agent:
                    serving_agent.complete_service(assigned_customer)
                    print(f"Customer {assigned_customer.customer_id} service completed by agent {serving_agent.agent_id}")
                    
                    with history_lock:
                        service_history.append(assigned_customer.to_dict())
        else:
            # Wait a bit before trying again
            time.sleep(0.5)

def status_updater():
    """Update agent statuses every 5 seconds"""
    while True:
        time.sleep(5)
        with agent_lock:
            for agent in agents:
                agent.update_status()
        print("Agent statuses updated")

# Initialize the system with some agents
def init_system():
    agent_names = ["Alex", "Blake", "Casey", "Dana", "Elliot", "Frankie", "Gray", "Harper", "Indigo", "Jordan"]
    for i in range(5):
        agent_id = str(uuid.uuid4())[:8]
        name = agent_names[i]
        workload_limit = random.randint(1, 3)
        new_agent = Agent(agent_id, name, workload_limit)
        with agent_lock:
            agents.append(new_agent)
    print(f"System initialized with {len(agents)} agents")

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bank Queue Management System</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f0f4f8;
            color: #2d3748;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background-color: #1a365d;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h1, h2, h3 {
            margin: 0;
        }
        .dashboard {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .metric-card {
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            text-align: center;
        }
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            color: #2c5282;
            margin: 10px 0;
        }
        .metric-label {
            font-size: 14px;
            color: #718096;
        }
        .panel {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        .panel h2 {
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 10px;
            margin-bottom: 20px;
            color: #2d3748;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background-color: #f7fafc;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f7fafc;
        }
        .status {
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-available {
            background-color: #c6f6d5;
            color: #22543d;
        }
        .status-busy {
            background-color: #fed7d7;
            color: #822727;
        }
        .priority-vip {
            background-color: #feebc8;
            color: #744210;
        }
        .priority-corporate {
            background-color: #e9d8fd;
            color: #553c9a;
        }
        .priority-normal {
            background-color: #bee3f8;
            color: #2c5282;
        }
        .algorithm-selector {
            margin-bottom: 20px;
            text-align: center;
        }
        .algorithm-selector button {
            background-color: #cbd5e0;
            border: none;
            padding: 10px 20px;
            margin: 0 5px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .algorithm-selector button.active {
            background-color: #4299e1;
            color: white;
        }
        .algorithm-selector button:hover {
            background-color: #a0aec0;
        }
        .progress-bar {
            height: 10px;
            background-color: #e2e8f0;
            border-radius: 5px;
            overflow: hidden;
            margin-top: 5px;
        }
        .progress-fill {
            height: 100%;
            background-color: #4299e1;
            transition: width 0.3s ease;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #718096;
            font-size: 14px;
        }
        @media (max-width: 768px) {
            .dashboard {
                grid-template-columns: 1fr;
            }
            .metrics {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Bank Queue Management System</h1>
            <p>Real-time customer service monitoring and optimization</p>
        </header>
        
        <div class="algorithm-selector">
            <h3>Current Algorithm: <span id="current-algorithm">Round Robin</span></h3>
            <div style="margin-top: 10px;">
                <button id="round-robin" class="active">Round Robin</button>
                <button id="priority">Priority</button>
                <button id="shortest-job">Shortest Job</button>
            </div>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">Average Wait Time</div>
                <div class="metric-value" id="avg-wait-time">0s</div>
                <div class="metric-label">Seconds</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Agent Utilization</div>
                <div class="metric-value" id="agent-utilization">0%</div>
                <div class="metric-label">Efficiency</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Fairness Score</div>
                <div class="metric-value" id="fairness-score">100</div>
                <div class="metric-label">Distribution</div>
            </div>
        </div>
        
        <div class="dashboard">
            <div class="panel">
                <h2>Agent Status</h2>
                <table id="agents-table">
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Workload</th>
                            <th>Status</th>
                            <th>Utilization</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Populated by JavaScript -->
                    </tbody>
                </table>
            </div>
            <div class="panel">
                <h2>Customer Queue</h2>
                <table id="queue-table">
                    <thead>
                        <tr>
                            <th>Customer ID</th>
                            <th>Priority</th>
                            <th>Service Time</th>
                            <th>Arrival Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Populated by JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="panel">
            <h2>Service History</h2>
            <table id="history-table">
                <thead>
                    <tr>
                        <th>Customer ID</th>
                        <th>Priority</th>
                        <th>Service Time</th>
                        <th>Wait Time</th>
                        <th>Agent</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Populated by JavaScript -->
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>© 2025 Bank Queue Management System | Refreshes every 5 seconds</p>
        </div>
    </div>

    <script>
        // Update interval in ms
        const UPDATE_INTERVAL = 5000;
        
        // DOM elements
        const agentsTable = document.getElementById('agents-table').getElementsByTagName('tbody')[0];
        const queueTable = document.getElementById('queue-table').getElementsByTagName('tbody')[0];
        const historyTable = document.getElementById('history-table').getElementsByTagName('tbody')[0];
        const avgWaitTime = document.getElementById('avg-wait-time');
        const agentUtilization = document.getElementById('agent-utilization');
        const fairnessScore = document.getElementById('fairness-score');
        const currentAlgorithm = document.getElementById('current-algorithm');
        
        // Algorithm buttons
        const roundRobinBtn = document.getElementById('round-robin');
        const priorityBtn = document.getElementById('priority');
        const shortestJobBtn = document.getElementById('shortest-job');
        
        // Set active algorithm
        function setActiveAlgorithm(algorithm) {
            // Reset all buttons
            roundRobinBtn.classList.remove('active');
            priorityBtn.classList.remove('active');
            shortestJobBtn.classList.remove('active');
            
            // Set active button
            if (algorithm === 'Round Robin') {
                roundRobinBtn.classList.add('active');
            } else if (algorithm === 'Priority Scheduling') {
                priorityBtn.classList.add('active');
            } else if (algorithm === 'Shortest Job Next') {
                shortestJobBtn.classList.add('active');
            }
            
            currentAlgorithm.textContent = algorithm;
        }
        
        // Change algorithm
        roundRobinBtn.addEventListener('click', () => changeAlgorithm('round_robin'));
        priorityBtn.addEventListener('click', () => changeAlgorithm('priority'));
        shortestJobBtn.addEventListener('click', () => changeAlgorithm('shortest_job'));
        
        function changeAlgorithm(algorithm) {
            fetch(`/api/algorithm/${algorithm}`)
                .then(response => response.json())
                .then(data => {
                    setActiveAlgorithm(data.algorithm);
                });
        }
        
        // Fetch and update data
        function updateAgents() {
            fetch('/api/agents')
                .then(response => response.json())
                .then(agents => {
                    // Clear table
                    agentsTable.innerHTML = '';
                    
                    // Add rows
                    agents.forEach(agent => {
                        const row = agentsTable.insertRow();
                        
                        const nameCell = row.insertCell();
                        nameCell.textContent = agent.name;
                        
                        const workloadCell = row.insertCell();
                        workloadCell.innerHTML = `${agent.current_workload}/${agent.workload_limit} <div class="progress-bar"><div class="progress-fill" style="width: ${(agent.current_workload / agent.workload_limit) * 100}%"></div></div>`;
                        
                        const statusCell = row.insertCell();
                        statusCell.innerHTML = `<span class="status ${agent.available ? 'status-available' : 'status-busy'}">${agent.available ? 'Available' : 'Busy'}</span>`;
                        
                        const utilizationCell = row.insertCell();
                        utilizationCell.textContent = `${agent.utilization_rate}%`;
                    });
                });
        }
        
        function updateQueue() {
            fetch('/api/queue')
                .then(response => response.json())
                .then(queue => {
                    // Clear table
                    queueTable.innerHTML = '';
                    
                    // Add rows
                    queue.forEach(customer => {
                        const row = queueTable.insertRow();
                        
                        const idCell = row.insertCell();
                        idCell.textContent = customer.customer_id;
                        
                        const priorityCell = row.insertCell();
                        const priorityClass = customer.priority === 'VIP' ? 'priority-vip' : 
                                            customer.priority === 'Corporate' ? 'priority-corporate' : 'priority-normal';
                        priorityCell.innerHTML = `<span class="status ${priorityClass}">${customer.priority}</span>`;
                        
                        const serviceTimeCell = row.insertCell();
                        serviceTimeCell.textContent = `${customer.service_time}s`;
                        
                        const arrivalTimeCell = row.insertCell();
                        arrivalTimeCell.textContent = customer.arrival_time;
                    });
                });
        }
        
        function updateHistory() {
            fetch('/api/history')
                .then(response => response.json())
                .then(history => {
                    // Clear table
                    historyTable.innerHTML = '';
                    
                    // Add rows (most recent first)
                    history.slice().reverse().forEach(customer => {
                        const row = historyTable.insertRow();
                        
                        const idCell = row.insertCell();
                        idCell.textContent = customer.customer_id;
                        
                        const priorityCell = row.insertCell();
                        const priorityClass = customer.priority === 'VIP' ? 'priority-vip' : 
                                            customer.priority === 'Corporate' ? 'priority-corporate' : 'priority-normal';
                        priorityCell.innerHTML = `<span class="status ${priorityClass}">${customer.priority}</span>`;
                        
                        const serviceTimeCell = row.insertCell();
                        serviceTimeCell.textContent = `${customer.service_time}s`;
                        
                        const waitTimeCell = row.insertCell();
                        waitTimeCell.textContent = customer.wait_time !== 'N/A' ? `${customer.wait_time.toFixed(1)}s` : 'N/A';
                        
                        const agentCell = row.insertCell();
                        agentCell.textContent = customer.assigned_agent;
                    });
                });
        }
        
        function updateMetrics() {
            fetch('/api/metrics')
                .then(response => response.json())
                .then(metrics => {
                    avgWaitTime.textContent = `${metrics.average_wait_time}s`;
                    agentUtilization.textContent = `${metrics.agent_utilization}%`;
                    fairnessScore.textContent = `${metrics.fairness_score}`;
                    setActiveAlgorithm(metrics.active_algorithm);
                });
        }
        
        // Initial update
        updateAgents();
        updateQueue();
        updateHistory();
        updateMetrics();
        
        // Set update interval
        setInterval(() => {
            updateAgents();
            updateQueue();
            updateHistory();
            updateMetrics();
        }, UPDATE_INTERVAL);
    </script>
</body>
</html>
"""

# API Endpoints
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/agents')
def get_agents():
    with agent_lock:
        return jsonify([agent.to_dict() for agent in agents])

@app.route('/api/customers')
def get_customers():
    with customer_lock:
        return jsonify([customer.to_dict() for customer in customers])

@app.route('/api/queue')
def get_queue():
    with queue_lock:
        return jsonify([customer.to_dict() for customer in waiting_queue])

@app.route('/api/history')
def get_history():
    with history_lock:
        return jsonify(service_history)

@app.route('/api/metrics')
def get_metrics():
    with history_lock:
        completed_customers = len(service_history)
        
        if completed_customers > 0:
            avg_wait_time = sum(float(customer['wait_time']) for customer in service_history 
                               if customer['wait_time'] != 'N/A') / completed_customers
        else:
            avg_wait_time = 0
            
    with agent_lock:
        avg_utilization = sum(agent.calculate_utilization_rate() for agent in agents) / len(agents) if agents else 0
        
        # Calculate fairness (standard deviation of workload distribution)
        workloads = [agent.current_workload for agent in agents]
        if workloads:
            mean_workload = sum(workloads) / len(workloads)
            variance = sum((w - mean_workload) ** 2 for w in workloads) / len(workloads)
            fairness_score = 100 - (100 * (variance ** 0.5))  # Higher is better
        else:
            fairness_score = 100
            
    return jsonify({
        "average_wait_time": round(avg_wait_time, 2),
        "agent_utilization": round(avg_utilization, 2),
        "fairness_score": round(fairness_score, 2),
        "completed_customers": completed_customers,
        "customers_in_queue": len(waiting_queue),
        "active_algorithm": get_algorithm_name()
    })

@app.route('/api/algorithm/<algorithm>')
def set_algorithm(algorithm):
    global current_algorithm
    
    if algorithm == "round_robin":
        current_algorithm = round_robin_scheduling
    elif algorithm == "priority":
        current_algorithm = priority_scheduling
    elif algorithm == "shortest_job":
        current_algorithm = shortest_job_next
    else:
        return jsonify({"error": "Invalid algorithm"}), 400
        
    return jsonify({"success": True, "algorithm": get_algorithm_name()})

def get_algorithm_name():
    if current_algorithm == round_robin_scheduling:
        return "Round Robin"
    elif current_algorithm == priority_scheduling:
        return "Priority Scheduling"
    elif current_algorithm == shortest_job_next:
        return "Shortest Job Next"
    return "Unknown"

# Main function to run the simulation
def run_simulation():
    # Initialize system with agents
    init_system()
    
    # Start customer generator thread
    customer_thread = threading.Thread(target=customer_generator)
    customer_thread.daemon = True
    customer_thread.start()
    
    # Start service processor thread
    service_thread = threading.Thread(target=service_processor)
    service_thread.daemon = True
    service_thread.start()
    
    # Start status updater thread
    status_thread = threading.Thread(target=status_updater)
    status_thread.daemon = True
    status_thread.start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)

if __name__ == '__main__':
    run_simulation()