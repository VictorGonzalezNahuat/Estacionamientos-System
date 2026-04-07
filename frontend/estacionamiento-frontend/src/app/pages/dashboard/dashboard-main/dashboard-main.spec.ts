import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { DashboardMain } from './dashboard-main';

describe('DashboardMain', () => {
  let component: DashboardMain;
  let fixture: ComponentFixture<DashboardMain>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardMain],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DashboardMain);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
