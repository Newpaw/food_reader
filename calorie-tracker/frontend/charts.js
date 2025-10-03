// Charts and visualization functionality

// Load Chart.js from CDN
function loadChartJS() {
  return new Promise((resolve, reject) => {
    if (window.Chart) {
      resolve(window.Chart);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
    script.onload = () => resolve(window.Chart);
    script.onerror = () => reject(new Error('Failed to load Chart.js'));
    document.head.appendChild(script);
  });
}

// Create a daily calorie chart
async function createDailyCalorieChart(containerId, data) {
  await loadChartJS();
  
  const ctx = document.getElementById(containerId).getContext('2d');
  
  // Extract dates and calorie values (convert UTC to local)
  const labels = data.days.map(day => {
    const date = utcToLocal(day.date);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });
  
  const calorieValues = data.days.map(day => day.total_calories);
  
  // Calculate recommended daily intake (example: 2000 calories)
  const recommendedIntake = Array(labels.length).fill(2000);
  
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Calories Consumed',
          data: calorieValues,
          backgroundColor: 'rgba(76, 175, 80, 0.7)',
          borderColor: 'rgba(76, 175, 80, 1)',
          borderWidth: 1
        },
        {
          label: 'Recommended Intake',
          data: recommendedIntake,
          type: 'line',
          fill: false,
          borderColor: 'rgba(255, 99, 132, 1)',
          borderDash: [5, 5],
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Calories'
          }
        },
        x: {
          title: {
            display: true,
            text: 'Date'
          }
        }
      },
      plugins: {
        title: {
          display: true,
          text: 'Daily Calorie Intake'
        },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      }
    }
  });
}

// Create a macronutrient distribution chart
async function createMacronutrientChart(containerId, meals) {
  await loadChartJS();
  
  const ctx = document.getElementById(containerId).getContext('2d');
  
  // Calculate total macronutrients
  let totalProtein = 0;
  let totalFat = 0;
  let totalCarbs = 0;
  
  meals.forEach(meal => {
    totalProtein += meal.protein || 0;
    totalFat += meal.fat || 0;
    totalCarbs += meal.carbs || 0;
  });
  
  // Convert to calories (protein: 4 cal/g, fat: 9 cal/g, carbs: 4 cal/g)
  const proteinCalories = totalProtein * 4;
  const fatCalories = totalFat * 9;
  const carbCalories = totalCarbs * 4;
  
  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Protein', 'Fat', 'Carbs'],
      datasets: [{
        data: [proteinCalories, fatCalories, carbCalories],
        backgroundColor: [
          'rgba(54, 162, 235, 0.7)',
          'rgba(255, 99, 132, 0.7)',
          'rgba(255, 206, 86, 0.7)'
        ],
        borderColor: [
          'rgba(54, 162, 235, 1)',
          'rgba(255, 99, 132, 1)',
          'rgba(255, 206, 86, 1)'
        ],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Macronutrient Distribution (Calories)'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.raw || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = Math.round((value / total) * 100);
              return `${label}: ${value} cal (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

// Create a meal frequency chart
async function createMealFrequencyChart(containerId, data) {
  await loadChartJS();
  
  const ctx = document.getElementById(containerId).getContext('2d');
  
  // Extract dates and meal counts (convert UTC to local)
  const labels = data.days.map(day => {
    const date = utcToLocal(day.date);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });
  
  const mealCounts = data.days.map(day => day.meals);
  
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Number of Meals',
        data: mealCounts,
        backgroundColor: 'rgba(153, 102, 255, 0.2)',
        borderColor: 'rgba(153, 102, 255, 1)',
        borderWidth: 2,
        tension: 0.1,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            stepSize: 1
          },
          title: {
            display: true,
            text: 'Number of Meals'
          }
        },
        x: {
          title: {
            display: true,
            text: 'Date'
          }
        }
      },
      plugins: {
        title: {
          display: true,
          text: 'Meals per Day'
        }
      }
    }
  });
}

// Create a nutrient intake chart
async function createNutrientIntakeChart(containerId, meals) {
  await loadChartJS();
  
  const ctx = document.getElementById(containerId).getContext('2d');
  
  // Group meals by date
  const mealsByDate = {};
  
  meals.forEach(meal => {
    const localDate = utcToLocal(meal.consumed_at);
    const date = localDate.toLocaleDateString('en-US');
    if (!mealsByDate[date]) {
      mealsByDate[date] = [];
    }
    mealsByDate[date].push(meal);
  });
  
  // Calculate daily nutrient totals
  const dates = Object.keys(mealsByDate).sort((a, b) => new Date(a) - new Date(b));
  const dailyProtein = [];
  const dailyFat = [];
  const dailyCarbs = [];
  const dailyFiber = [];
  
  dates.forEach(date => {
    const meals = mealsByDate[date];
    let protein = 0, fat = 0, carbs = 0, fiber = 0;
    
    meals.forEach(meal => {
      protein += meal.protein || 0;
      fat += meal.fat || 0;
      carbs += meal.carbs || 0;
      fiber += meal.fiber || 0;
    });
    
    dailyProtein.push(protein);
    dailyFat.push(fat);
    dailyCarbs.push(carbs);
    dailyFiber.push(fiber);
  });
  
  // Format dates for display (already in local timezone)
  const formattedDates = dates.map(date => {
    const d = new Date(date);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  });
  
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: formattedDates,
      datasets: [
        {
          label: 'Protein (g)',
          data: dailyProtein,
          borderColor: 'rgba(54, 162, 235, 1)',
          backgroundColor: 'rgba(54, 162, 235, 0.1)',
          borderWidth: 2,
          fill: false
        },
        {
          label: 'Fat (g)',
          data: dailyFat,
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          borderWidth: 2,
          fill: false
        },
        {
          label: 'Carbs (g)',
          data: dailyCarbs,
          borderColor: 'rgba(255, 206, 86, 1)',
          backgroundColor: 'rgba(255, 206, 86, 0.1)',
          borderWidth: 2,
          fill: false
        },
        {
          label: 'Fiber (g)',
          data: dailyFiber,
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.1)',
          borderWidth: 2,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Grams'
          }
        },
        x: {
          title: {
            display: true,
            text: 'Date'
          }
        }
      },
      plugins: {
        title: {
          display: true,
          text: 'Daily Nutrient Intake'
        },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      }
    }
  });
}