//import Chart from 'https://cdn.jsdelivr.net/npm/chart.js@3.8.0/dist/chart.esm.min.js';

document.addEventListener('DOMContentLoaded', function() {
    const loadingMessage = document.getElementById('loadingMessage');
    const chartLoadingMessage = document.getElementById('chartLoadingMessage');
    const fileDropdown = document.getElementById('file_id');
    const strategySelect = document.getElementById('strategySelect');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const loadFilesButton = document.getElementById('loadFiles');
    const resetFilesButton = document.getElementById('resetFiles');
    const plotAvgButton = document.getElementById('plotAvg');

    function fetchFiles(startDate = '', endDate = '', strategy = '') {
        loadingMessage.style.display = 'block'; // Show loading message

        // Construct the query string with optional parameters
        const queryString = new URLSearchParams({
            start_date: startDate,
            end_date: endDate,
            strategy: strategy
        }).toString();

        fetch('/files?' + queryString)
            .then(response => response.json())
            .then(data => {
                loadingMessage.style.display = 'none'; // Hide loading message

                console.log('Received file data:', data); // 데이터 로깅
                if (!fileDropdown) {
                    console.error('Dropdown element not found');
                    return;
                }
                if (data.length === 0) {
                    console.warn('No file data received');
                    return;
                }
                fileDropdown.innerHTML = '<option value="">--Select a date--</option>'; // Reset options
                data.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file.id;
                    option.textContent = file.date || file.name; // date가 없으면 name 사용
                    fileDropdown.appendChild(option);
                });
            })
            .catch(error => {
                loadingMessage.style.display = 'none'; // Hide loading message on error
                console.error('Error fetching file list:', error);
            });
    }

    function updateFileDropdown() {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const strategy = strategySelect.value;
        fetchFiles(startDate, endDate, strategy);
    }

    loadFilesButton.addEventListener('click', function() {
        updateFileDropdown();
    });

//################

    function plotAverage() {
        chartLoadingMessage.style.display = 'block'; // Show chart loading message

        // Collect all file IDs from the dropdown
        const fileIds = Array.from(fileDropdown.options)
            .filter(option => option.value)  // Remove options without value
            .map(option => option.value);

        if (fileIds.length === 0) {
            console.error('No files available in the dropdown.');
            alert('No files available to plot.');
            return;
        }

        // Colors for different files
        const colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8'];

        Promise.all(fileIds.map((fileId, index) =>
            fetch('/data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: new URLSearchParams({
                    'file_id': fileId
                })
            }).then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            }).catch(error => {
                console.error(`Error fetching data for file ${fileId}:`, error);
                return []; // Return empty array in case of error
            })
        ))
        .then(results => {
            chartLoadingMessage.style.display = 'none'; // Hide chart loading message

            // Prepare datasets for the chart
            const datasets = [];
            const allPrfData = [];
            const allLengths = [];
            const timeSets = [];

            results.forEach((data, index) => {
                const color = colors[index % colors.length]; // Use different colors for different files

                // Convert data to time and prf arrays
                const timeData = data.map(row => new Date(row.time));
                const prfData = data.map(row => parseFloat(row.prf));

                timeSets.push(timeData);

                allPrfData.push(prfData);
                allLengths.push(prfData.length);

                // Create dataset for the file
                datasets.push({
                    label: `File ${index + 1}`, // Use file name or date if available
                    data: data.map(row => ({
                        x: new Date(row.time), // Convert time to Date object
                        y: parseFloat(row.prf)
                    })),
                    borderColor: color,
                    backgroundColor: color + '20', // Add transparency
                    borderWidth: 2,
                    fill: false
                });
            });

            if (datasets.length === 0) {
                console.error('No valid data available for plotting.');
                alert('No data available to plot.');
                return;
            }

            // Create the average line
            const maxLength = Math.max(...allLengths);
            const xNew = Array.from({ length: maxLength }, (_, i) => i);

            const interpolatedData = allPrfData.map(prfArray => {
                const xOld = Array.from({ length: prfArray.length }, (_, i) => i);
                return xNew.map(x => {
                    const oldIndex = Math.min(xOld.length - 1, Math.max(0, Math.floor(x)));
                    const nextIndex = Math.min(oldIndex + 1, xOld.length - 1);
                    const t = x - oldIndex;
                    return prfArray[oldIndex] * (1 - t) + prfArray[nextIndex] * t;
                });
            });

            const avgPrf = interpolatedData.reduce((acc, val) => val.map((v, i) => (acc[i] || 0) + v), []);
            const avgPrfLine = avgPrf.map(v => v / interpolatedData.length);

            datasets.push({
                label: 'Average PRF',
                data: xNew.map(x => ({
                    x: xNew[x],
                    y: avgPrfLine[x]
                })),
                borderColor: '#000000',
                backgroundColor: '#00000020',
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false
            });

            // Draw the chart
            const ctx = document.getElementById('myChart').getContext('2d');

            // Ensure `window.myChart` is a valid Chart instance before calling destroy
            if (window.myChart && window.myChart instanceof Chart) {
                window.myChart.destroy();
            }

            window.myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'minute', // Adjust according to the time granularity
                                tooltipFormat: 'll HH:mm'
                            },
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'PRF'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            chartLoadingMessage.style.display = 'none'; // Hide chart loading message on error
            console.error('Error processing data for chart:', error);
        });
    }


//################

    plotAvgButton.addEventListener('click', function() {
        plotAverage();
    });


    // Add event listener for the reset button
    resetFilesButton.addEventListener('click', function() {
        // Clear the date inputs
        startDateInput.value = '';
        endDateInput.value = '';

        // Optionally, you might want to trigger a load or update to refresh the file list
        updateFileDropdown();
    });

    strategySelect.addEventListener('change', function() {
        // Optional: Update file dropdown when strategy changes
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        const strategy = strategySelect.value;
        fetchFiles(startDate, endDate, strategy);
    });

    document.getElementById('fileForm').addEventListener('submit', function(event) {
        event.preventDefault();
        const fileId = fileDropdown.value;

        chartLoadingMessage.style.display = 'block'; // Show chart loading message

        fetch('/data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                'file_id': fileId
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            chartLoadingMessage.style.display = 'none'; // Hide chart loading message

            console.log('Data received from backend:', data);

            if (data.error) {
                console.error('Error:', data.error);
                return;
            }

            const labels = data.map(row => row['time']);
            const priceValues = data.map(row => row['price']);
            const np1Values = data.map(row => row['np1']);
            const np2Values = data.map(row => row['np2']);
            const prfValues = data.map(row => row['prf']);

            const ctx = document.getElementById('myChart').getContext('2d');

            // Ensure `window.myChart` is a valid Chart instance before calling destroy
            if (window.myChart && window.myChart instanceof Chart) {
                window.myChart.destroy();
            }

            window.myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'price',
                            data: priceValues,
                            borderColor: '#4e73df',
                            backgroundColor: 'rgba(78, 115, 223, 0.2)',
                            borderWidth: 2,
                            pointRadius: 0.5,
                            fill: false,
                            yAxisID: 'y1'
                        },
                        {
                            label: 'long',
                            data: np1Values,
                            borderColor: '#28a745',  // 밝은 녹색으로 변경
                            backgroundColor: 'rgba(40, 167, 69, 0.2)',  // 밝은 녹색의 반투명 배경
                            borderWidth: 1,
                            pointRadius: 0.2,
                            fill: true,
                            yAxisID: 'y2'
                        },
                        {
                            label: 'short',
                            data: np2Values,
                            borderColor: '#b73d3d',  // 어두운 붉은색
                            backgroundColor: 'rgba(183, 61, 61, 0.2)',  // 어두운 붉은색의 반투명 배경
                            borderWidth: 1,
                            pointRadius: 0.2,
                            fill: true,
                            yAxisID: 'y2'
                        },
                        {
                            label: 'profit',
                            data: prfValues,
                            borderColor: '#f00',  // 빨간색으로 변경
                            backgroundColor: 'rgba(255, 0, 0, 0.2)',  // 빨간색의 반투명 배경
                            borderWidth: 3,
                            pointRadius: 0.7,
                            fill: false,
                            yAxisID: 'y2'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Time',
                                color: '#858796',
                                font: {
                                    size: 14
                                }
                            },
                            grid: {
                                display: false
                            }
                        },
                        y1: {
                            type: 'linear',
                            position: 'left',
                            title: {
                                display: true,
                                text: 'price',
                                color: '#4e73df',
                                font: {
                                    size: 14
                                }
                            },
                            ticks: {
                                beginAtZero: true,
                                color: '#4e73df'
                            },
                            grid: {
                                drawBorder: false,
                                borderDash: [2, 2],
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        y2: {
                            type: 'linear',
                            position: 'right',
                            title: {
                                display: true,
                                text: 'long, short, and profit',
                                color: '#e74a3b',
                                font: {
                                    size: 14
                                }
                            },
                            ticks: {
                                beginAtZero: true,
                                color: '#e74a3b'
                            },
                            grid: {
                                drawOnChartArea: false
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#858796',
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: '#f8f9fc',
                            bodyColor: '#858796',
                            borderColor: '#e3e6f0',
                            borderWidth: 1,
                            callbacks: {
                                label: function(tooltipItem) {
                                    return tooltipItem.dataset.label + ': ' + tooltipItem.raw;
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            chartLoadingMessage.style.display = 'none'; // Hide chart loading message on error
            console.error('Error fetching data:', error);
        });
    });
});
