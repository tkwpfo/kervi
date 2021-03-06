import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { ActivatedRoute, Router} from '@angular/router';
import { KerviDashboardComponent} from 'ngx-kervi'
declare var window:any;
@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent extends KerviDashboardComponent implements OnInit {
  @ViewChild("leftPad") leftPad:ElementRef;
  @ViewChild("rightPad") rightPad:ElementRef;
  private padSize=180;
  public leftPadTop:number;
  public leftPadLeft:number;
  
  public rightPadTop:number;
  public rightPadLeft:number;
  constructor(private router:Router, private activatedRoute:ActivatedRoute) {
    super();
   }

  ngOnInit() {
    var self = this;
    //this.router.url;
    //console.log("r", this.activatedRoute.params.subscribe)
    this.activatedRoute.params.subscribe(params => {
      var dashboardId = params['name']; 
      this.loadDashboard(dashboardId);
      console.log("rid", dashboardId);
      
      setTimeout(() => {
        var h = window.innerHeight;
        var w = window.innerWidth;

        self.leftPadTop = h / 2 - self.padSize/2
        self.leftPadLeft = w / 4 - self.padSize/2 
        
        self.rightPadTop = h / 2 - self.padSize/2
        self.rightPadLeft = w - w / 4 - self.padSize/2 
        

      }, 0);
      


    //   this.dashboardsService.getDashboards$().subscribe(function(v){
    //     self.setupDashboard()
     })
  }

}
