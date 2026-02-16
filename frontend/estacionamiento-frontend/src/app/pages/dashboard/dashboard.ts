import { Component, HostListener } from '@angular/core';
import { RouterOutlet } from "@angular/router";

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
  imports: [RouterOutlet],
})
export class Dashboard {

  openMenu: string | null = null;

  toggleMenu(menu: string): void {
    this.openMenu = this.openMenu === menu ? null : menu;
  }

  navigate(): void {
    this.openMenu = null;
  }

  @HostListener('document:click')
  closeMenu(): void {
    this.openMenu = null;
  }

}
