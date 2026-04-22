import {
  HttpInterceptorFn,
  HttpRequest,
  HttpEvent,
  HttpHandlerFn,
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export const apiInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const apiReq = req.clone({
    url: getApiUrl(req.url),
    withCredentials: true,
  });

  return next(apiReq);
};

function getApiUrl(url: string): string {
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  const baseUrl = environment.apiUrl;

  if (url.startsWith('/api') || url.startsWith('api/')) {
    return url.startsWith('/') ? `${baseUrl}${url.replace('/api', '')}` : `${baseUrl}/${url.replace('api/', '')}`;
  }

  return `${baseUrl}/${url}`;
}
