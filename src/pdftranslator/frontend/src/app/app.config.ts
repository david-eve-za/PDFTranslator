import { ApplicationConfig, provideBrowserGlobalErrorListeners, importProvidersFrom } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { InMemoryWebApiModule } from 'angular-in-memory-web-api';

import { routes } from './app.routes';
import { apiInterceptor } from './core/interceptors/api.interceptor';
import { InMemoryDataService } from './core/mock/in-memory-data.service';
import { environment } from '../environments/environment';

const providers: any[] = [
  provideBrowserGlobalErrorListeners(),
  provideRouter(routes),
  provideHttpClient(withInterceptors([apiInterceptor]))
];

// Only load InMemoryWebAPI in development with mock data enabled
if (environment.useMockData) {
  providers.push(
    importProvidersFrom(InMemoryWebApiModule.forRoot(InMemoryDataService, { delay: 500 }))
  );
}

export const appConfig: ApplicationConfig = { providers };
