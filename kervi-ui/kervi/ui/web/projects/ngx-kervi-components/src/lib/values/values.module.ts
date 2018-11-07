import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common'
import { NumberComponent} from './number-value/number-value.component'
import { NGXKerviPipesModule  } from 'ngx-kervi'

import { BooleanComponent} from './boolean-value/boolean-value.component'
// import { StringComponent} from './string-value/string-value.component'
// import { DateTimeComponent} from './datetime-value/datetime-value.component'
// import { ColorComponent} from './color-value/color-value.component'
// import { EnumComponent} from './enum-value/enum-value.component'
import { ActionComponent } from './action/action.component';

import { KerviValueComponent } from './kervi-value/kervi-value.component'
import { UIComponentsModule} from '../ui-components/ui-components.module'
@NgModule({
  declarations: [
    ActionComponent,
    NumberComponent,
    BooleanComponent,
    KerviValueComponent,
    //BooleanComponent,
    //StringComponent,
    //EnumComponent,
    //DateTimeComponent,
    //ColorComponent
  ],
  exports:[
      ActionComponent,
      NumberComponent,
      BooleanComponent,
      KerviValueComponent,
      //BooleanComponent,
      //StringComponent,
      //EnumComponent,
      //DateTimeComponent,
      //ColorComponent
  ],
  imports: [
    CommonModule,
    UIComponentsModule,
    NGXKerviPipesModule
  ],
  providers: [],
  bootstrap: []
})
export class ValuesModule {
  constructor (){}
}
