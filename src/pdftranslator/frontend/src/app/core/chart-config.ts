import { Chart } from 'chart.js';
import * as ChartControllers from 'chart.js';

// Chart.js 4.x requires explicit registration of controllers
Chart.register(
  ChartControllers.DoughnutController,
  ChartControllers.ArcElement,
  ChartControllers.Legend,
  ChartControllers.Tooltip
);
