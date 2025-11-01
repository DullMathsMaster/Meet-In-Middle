// Main JavaScript for the meeting location optimizer

document.addEventListener('DOMContentLoaded', function() {
    // Optimize button
    document.getElementById('optimize-btn').addEventListener('click', optimizeLocation);
    
    // Load sample button
    document.getElementById('load-sample-btn').addEventListener('click', loadSample);

    async function optimizeLocation() {
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const error = document.getElementById('error');

        // Hide previous results
        results.style.display = 'none';
        error.style.display = 'none';
        loading.style.display = 'block';

        try {
            // Collect input data
            const attendeesText = document.getElementById('attendees-input').value;
            const attendees = JSON.parse(attendeesText);

            const startDate = document.getElementById('availability-start').value;
            const endDate = document.getElementById('availability-end').value;

            const durationDays = parseInt(document.getElementById('duration-days').value) || 0;
            const durationHours = parseInt(document.getElementById('duration-hours').value) || 0;

            // Convert local datetime to ISO format
            const startISO = new Date(startDate).toISOString();
            const endISO = new Date(endDate).toISOString();

            const inputData = {
                attendees: attendees,
                availability_window: {
                    start: startISO,
                    end: endISO
                },
                event_duration: {
                    days: durationDays,
                    hours: durationHours
                }
            };

            // Call API
            const response = await fetch('/api/optimize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(inputData)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Optimization failed');
            }

            // Display results
            displayResults(data);
            loading.style.display = 'none';
            results.style.display = 'block';

        } catch (err) {
            loading.style.display = 'none';
            error.style.display = 'block';
            error.textContent = `Error: ${err.message}`;
        }
    }

    function displayResults(data) {
        const solution = data.solution;

        // Main solution
        document.getElementById('solution-location').textContent = 
            `📍 ${solution.event_location}`;
        document.getElementById('total-co2').textContent = `${solution.total_co2} kg`;
        document.getElementById('avg-travel').textContent = `${solution.average_travel_hours} hrs`;
        document.getElementById('median-travel').textContent = `${solution.median_travel_hours} hrs`;
        document.getElementById('fairness-score').textContent = solution.fairness_score.toFixed(4);

        // Rationale
        const rationale = document.getElementById('rationale');
        rationale.innerHTML = `
            <p><strong>Location Selection Rationale:</strong></p>
            <p>${solution.event_location} was selected as the optimal meeting location based on a balanced 
            consideration of environmental impact and travel fairness. Using equal weighting between emissions and fairness, this location minimizes total carbon emissions 
            (${solution.total_co2} kg CO₂) while maintaining reasonable travel time disparities across all offices.</p>
            <p>The median travel time of ${solution.median_travel_hours} hours indicates that most attendees 
            have manageable journeys, while the fairness score of ${solution.fairness_score.toFixed(4)} reflects 
            the balance achieved between offices with varying distances.</p>
        `;

        // Travel breakdown
        const breakdown = document.getElementById('travel-breakdown');
        let breakdownHTML = '';
        for (const [office, hours] of Object.entries(solution.attendee_travel_hours)) {
            breakdownHTML += `
                <div class="travel-item">
                    <span><strong>${office}</strong></span>
                    <span>${hours.toFixed(2)} hours</span>
                </div>
            `;
        }
        breakdown.innerHTML = breakdownHTML;

        // Alternatives
        const alternatives = document.getElementById('alternatives');
        if (data.alternatives && data.alternatives.length > 0) {
            let altHTML = '';
            data.alternatives.slice(0, 5).forEach(alt => {
                altHTML += `
                    <div class="alternative-item">
                        <h4>${alt.event_location}</h4>
                        <div class="alternative-metrics">
                            <div class="alternative-metric">
                                <label>Total CO₂</label>
                                <value>${alt.total_co2} kg</value>
                            </div>
                            <div class="alternative-metric">
                                <label>Avg Travel</label>
                                <value>${alt.average_travel_hours} hrs</value>
                            </div>
                            <div class="alternative-metric">
                                <label>Fairness</label>
                                <value>${alt.fairness_score.toFixed(4)}</value>
                            </div>
                        </div>
                    </div>
                `;
            });
            alternatives.innerHTML = altHTML;
        } else {
            alternatives.innerHTML = '<p>No alternatives available.</p>';
        }

        // Charts
        if (data.visualization && data.visualization.chart_data) {
            displayCharts(data.visualization.chart_data, data.alternatives ? [solution, ...data.alternatives] : [solution]);
        }

        // Map
        if (data.visualization && data.visualization.map_path) {
            document.getElementById('map-frame').src = data.visualization.map_path;
        }
    }

    function displayCharts(chartData, allSolutions) {
        const chartsDiv = document.getElementById('charts');
        
        // CO2 Comparison Chart
        const co2Trace = {
            x: allSolutions.map(s => s.event_location),
            y: allSolutions.map(s => s.total_co2),
            type: 'bar',
            marker: { color: '#667eea' },
            name: 'Total CO₂ (kg)'
        };

        const co2Layout = {
            title: 'Total CO₂ Emissions by Location',
            xaxis: { title: 'Location' },
            yaxis: { title: 'CO₂ (kg)' },
            margin: { t: 50, r: 50, b: 100, l: 50 }
        };

        const co2Div = document.createElement('div');
        co2Div.id = 'co2-chart';
        chartsDiv.appendChild(co2Div);
        Plotly.newPlot('co2-chart', [co2Trace], co2Layout);

        // Travel Time Comparison Chart
        const travelTrace = {
            x: allSolutions.map(s => s.event_location),
            y: allSolutions.map(s => s.average_travel_hours),
            type: 'bar',
            marker: { color: '#764ba2' },
            name: 'Average Travel Hours'
        };

        const travelLayout = {
            title: 'Average Travel Time by Location',
            xaxis: { title: 'Location' },
            yaxis: { title: 'Travel Hours' },
            margin: { t: 50, r: 50, b: 100, l: 50 }
        };

        const travelDiv = document.createElement('div');
        travelDiv.id = 'travel-chart';
        travelDiv.style.marginTop = '20px';
        chartsDiv.appendChild(travelDiv);
        Plotly.newPlot('travel-chart', [travelTrace], travelLayout);

        // Fairness Comparison
        const fairnessTrace = {
            x: allSolutions.map(s => s.event_location),
            y: allSolutions.map(s => s.fairness_score || 0),
            type: 'bar',
            marker: { color: '#ff6b6b' },
            name: 'Fairness Score'
        };

        const fairnessLayout = {
            title: 'Fairness Score by Location (lower is better)',
            xaxis: { title: 'Location' },
            yaxis: { title: 'Fairness Score' },
            margin: { t: 50, r: 50, b: 100, l: 50 }
        };

        const fairnessDiv = document.createElement('div');
        fairnessDiv.id = 'fairness-chart';
        fairnessDiv.style.marginTop = '20px';
        chartsDiv.appendChild(fairnessDiv);
        Plotly.newPlot('fairness-chart', [fairnessTrace], fairnessLayout);
    }

    function loadSample() {
        const sampleData = {
            "Mumbai": 2,
            "Shanghai": 3,
            "Hong Kong": 1,
            "Singapore": 2,
            "Sydney": 2
        };
        
        document.getElementById('attendees-input').value = JSON.stringify(sampleData, null, 2);
    }
});

