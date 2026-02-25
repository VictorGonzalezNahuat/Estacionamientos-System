import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AlertService } from '../../../core/services/alert';

@Component({
  selector: 'app-global-alert',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './global-alert.html',
  styleUrls: ['./global-alert.css']
})
export class GlobalAlert {

  alertService = inject(AlertService);

}
