import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { ReimpresionTickets } from './reimpresion-tickets';

describe('ReimpresionTickets', () => {
  let component: ReimpresionTickets;
  let fixture: ComponentFixture<ReimpresionTickets>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReimpresionTickets, HttpClientTestingModule]
    })
    .compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ReimpresionTickets);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const request = httpMock.expectOne('/estacionamiento/reimpresion/ultimos');
    request.flush({ data: [] });
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
