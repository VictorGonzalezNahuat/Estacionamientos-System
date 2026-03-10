import { Component, ChangeDetectionStrategy } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-dashboard-main',
  imports: [RouterLink],
  templateUrl: './dashboard-main.html',
  styleUrl: './dashboard-main.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardMain {

}
