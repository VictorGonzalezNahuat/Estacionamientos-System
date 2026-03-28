import { bootstrapApplication } from '@angular/platform-browser';
import { App } from './app/app';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { routes } from './app/app.routes';
import { provideRouter } from '@angular/router';
import { authInterceptor } from './app/interceptors/auth-interceptor';
import { APP_INITIALIZER } from '@angular/core';
import { ConfigService } from './app/services/config.service';
import { provideServiceWorker } from '@angular/service-worker';
import { isDevMode } from '@angular/core';

function initializeApp(configService: ConfigService) {
  return () => configService.loadConfig();
}

bootstrapApplication(App, {
  providers: [ 
    provideRouter(routes),
    provideHttpClient(
      withInterceptors([authInterceptor])
    ),
    {
      provide: APP_INITIALIZER,
      useFactory: initializeApp,
      deps: [ConfigService],
      multi: true
    },
    provideServiceWorker('ngsw-worker.js', {
      enabled: !isDevMode(),
      registrationStrategy: 'registerWhenStable:30000'
    })
  ]
});
