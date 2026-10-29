import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subscription } from 'rxjs';
import { AlertMessage, AlertService } from '../../servicios/alertService';

@Component({
  selector: 'app-alertas',
  imports: [],
  templateUrl: './alertas.html',
})
export class Alertas implements OnInit, OnDestroy{
  alerts: AlertMessage[] = [];
  private sub = new Subscription();

  constructor(private alertService: AlertService) {}

  ngOnInit(): void {
    this.sub.add(
      this.alertService.alert$.subscribe((alert) => {
        //si es confirm, NO lo tratamos como toast
        if (alert.type === 'confirm') {
          this.alerts = [alert]; // solo uno visible tipo modal
          return;
        }

        this.alerts.push(alert);

        const timeout = alert.timeout ?? 3500;
        if (timeout > 0) {
          setTimeout(() => this.remove(alert.id), timeout);
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  remove(id: number) {
    this.alerts = this.alerts.filter((a) => a.id !== id);
  }

  accept(alert: AlertMessage) {
    alert.resolve?.(true);
    this.alerts = [];
  }

  cancel(alert: AlertMessage) {
    alert.resolve?.(false);
    this.alerts = [];
  }

}