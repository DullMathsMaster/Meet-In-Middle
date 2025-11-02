// Main JavaScript for the meeting location optimizer

document.addEventListener('DOMContentLoaded', function() {
    const optimizeButton = document.getElementById('optimize-btn');
    const loadSampleButton = document.getElementById('load-sample-btn');
    const fileUploadInput = document.getElementById('json-upload');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const error = document.getElementById('error');

    if (optimizeButton) {
        optimizeButton.addEventListener('click', optimizeLocation);
    }

    if (loadSampleButton) {
        loadSampleButton.addEventListener('click', loadSample);
    }

    if (fileUploadInput) {
        fileUploadInput.addEventListener('change', handleJsonUpload);
    }


    function clearError() {
        if (!error) {
            return;
        }
        error.style.display = 'none';
        error.textContent = '';
    }

    function showError(message) {
        if (!error) {
            return;
        }
        error.style.display = 'block';
        error.textContent = `Error: ${message}`;
        if (results) {
            results.style.display = 'none';
        }
        if (loading) {
            loading.style.display = 'none';
        }
    }

    async function optimizeLocation() {
        if (!loading || !results) {
            return;
        }
        // Hide previous results
        results.style.display = 'none';
        clearError();
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
            showError(err.message);
        }
    }

    function handleJsonUpload(event) {
        const file = event.target.files && event.target.files[0];
        if (!file) {
            return;
        }

        const reader = new FileReader();
        reader.onload = (loadEvent) => {
            try {
                const payload = JSON.parse(loadEvent.target.result);
                if (!payload.attendees || !payload.availability_window || !payload.event_duration) {
                    throw new Error('JSON missing required attendees, availability_window, or event_duration.');
                }

                const attendeesInput = document.getElementById('attendees-input');
                if (attendeesInput) {
                    attendeesInput.value = JSON.stringify(payload.attendees, null, 2);
                }

                if (payload.availability_window.start) {
                    setDateInputValue('availability-start', payload.availability_window.start);
                }
                if (payload.availability_window.end) {
                    setDateInputValue('availability-end', payload.availability_window.end);
                }

                if (typeof payload.event_duration.days !== 'undefined') {
                    const daysField = document.getElementById('duration-days');
                    if (daysField) {
                        daysField.value = payload.event_duration.days;
                    }
                }

                if (typeof payload.event_duration.hours !== 'undefined') {
                    const hoursField = document.getElementById('duration-hours');
                    if (hoursField) {
                        hoursField.value = payload.event_duration.hours;
                    }
                }

                clearError();
            } catch (err) {
                showError(err.message);
            } finally {
                event.target.value = '';
            }
        };

        reader.onerror = () => {
            showError('Unable to read JSON file.');
            event.target.value = '';
        };

        reader.readAsText(file);
    }

    function setDateInputValue(elementId, isoString) {
        const targetInput = document.getElementById(elementId);
        if (!targetInput) {
            return;
        }

        const date = new Date(isoString);
        if (Number.isNaN(date.getTime())) {
            throw new Error(`Invalid date value for ${elementId}.`);
        }

        const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
        targetInput.value = local.toISOString().slice(0, 16);
    }

    function displayResults(data) {
        const solution = data.solution;

        if (document.getElementById('charts')) {
            document.getElementById('charts').innerHTML = '';
        }

        // Main solution
        document.getElementById('solution-location').textContent = 
            `📍 ${solution.event_location}`;
        document.getElementById('total-co2').textContent = `${solution.total_co2} kg`;
        document.getElementById('avg-travel').textContent = `${solution.average_travel_hours} hrs`;
        document.getElementById('median-travel').textContent = `${solution.median_travel_hours} hrs`;
        // Rationale
        const rationale = document.getElementById('rationale');
        rationale.innerHTML = `
            <p><strong>Location Selection Rationale:</strong></p>
            <p>${solution.event_location} delivered the lowest total emissions at ${solution.total_co2} kg CO₂ across all attendees.</p>
            <p>The median travel time of ${solution.median_travel_hours} hours keeps most journeys manageable, and the detailed breakdown below shows how long each office spends in transit.</p>
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
                                <label>Median Travel</label>
                                <value>${alt.median_travel_hours} hrs</value>
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
        chartsDiv.innerHTML = '';
        
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
        clearError();
    }
});

