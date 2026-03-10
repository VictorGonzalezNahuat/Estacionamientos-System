import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AlertService } from '../../../core/services/alert';

@Component({
  selector: 'app-global-alert',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './global-alert.html',
  styleUrls: ['./global-alert.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GlobalAlert {

  alertService = inject(AlertService);

}
