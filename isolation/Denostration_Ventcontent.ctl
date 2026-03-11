// $License: NOLICENSE
//--------------------------------------------------------------------------------
/**
  @file $relPath
  @copyright $copyright
  @author scadtech
*/

//--------------------------------------------------------------------------------
// Libraries used (#uses)

//--------------------------------------------------------------------------------
// Variables and Constants


//--------------------------------------------------------------------------------
//@public members
//--------------------------------------------------------------------------------
#uses "DCRInstruction.ctl"

class skifcontent
{
  public dyn_string stateDP;
  public dyn_string dp_scadtech(dyn_string dp)
  {
    for(int i = 1; i <= dynlen(dp); i++){
      stateDP.append(dp[i] + ".State.TimP");
    }
  }

};

class AI_scadtech:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".OIPVisualValue:_online.._value",
                               settings["dpName"] + ".Alarm:_online.._value",
                               settings["dpName"] + ".AlarmWarn:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
		string val;
		sprintf(val, "%.0f", value[1]);
    bool invalid = dpName + ":_online.._invalid";
    string HaveUnit = dpGetUnit(dpName[1]);

    if (HaveUnit == "") {
    setValueLib("unit", "text" , "???");
  } else {
    setValueLib("unit", "text", HaveUnit);
  }

    if (value[2])
      setValueLib("value", "foreCol", "red");
    else if (value[3])
      setValueLib("value", "foreCol", "yellow");
    else
      setValueLib("value", "foreCol", "normAI");

  if (false){
      setValueLib("value", "text", "___");
      setValueLib("value", "foreCol", "black");
    } else {
    setValueLib("value", "text", val);
    }
  }
};


class DI_scadtech:skifcontent
{
  public mapping stateMap = makeMapping(
      "iconON", makeDynString("visible", "FALSE"),
      "iconOFF", makeDynString("visible", "FALSE"),
      "ellipseON", makeDynString("visible", "FALSE"),
      "ellipseOFF", makeDynString("visible", "FALSE"),
      "textON", makeDynString("visible", "FALSE"),
      "textOFF", makeDynString("visible", "FALSE"),
      "backON", makeDynString("visible", "FALSE"),
      "backOFF", makeDynString("visible", "FALSE")
  );

  public void changeState(dyn_bool state, mapping key)
  {
    mapping map = key["KeyValues"];
    bool result;
    if (state.contains(true))
    {result = (true == map["invert"]);}
    else{result = (false == map["invert"]);}

    if (map["iconVisible"] == 1){
      stateMap["iconON"][2] = !result;
      stateMap["iconOFF"][2] = result;
    }
    if (map["ellipsesVisible"] == 1){
      stateMap["ellipseON"][2] = !result;
      stateMap["ellipseOFF"][2] = result;
    }
    if (map["textVisible"] == 1){
      stateMap["textON"][2] = !result;
      stateMap["textOFF"][2] = result;
    }
    if (map["backVisible"] == 1){
      stateMap["backON"][2] = !result;
      stateMap["backOFF"][2] = result;
    }
  }

//------------------------------------------------------------------------------------------------------------------//
  public void updateStateLight(mapping settings)
  {
    tooltip.toolTipText(dpGetDescription(dpSubStr(settings["dpName"], DPSUB_DP)+ "."));
   dyn_string dps;

//     dpConnect("updateStateReceiptCB", settings["dpName"] + ".State.TimP:_online.._value",
//                                       settings["dpName"] + ".State.TimP:_alert_hdl.._ack_possible");
            dps[1] = settings["dpName"] + ".State.TimP:_online.._value";
            dps[2] = settings["dpName"] + ".StSignState:_original.._value"; // Состояние сигнализации (13-й бит)
            dps[3] = DiagWarning(makeDynString(dps[1]));
            dps = MixDpsForUpdateState(dps);
//                 bacolDI.toolTipText(dpGetDescription(dpSubStr(settings["dpName"],DPSUB_DP)+ "."));
                        DebugN("updateStateLightCB", dps);

            if (dps[2] != "0" && dps[2] != "1")
            {
                dpConnect("updateStateLightCB", dps);
            }
            else
            {
                DebugN("SCADTECH_VENT One: Отсутствует адрес или не совпадает с существующими modPlc");
            }
  }

  public static updateStateLightCB(dyn_string dpName, dyn_anytype value)
  {
    bool stSignState = (value[1] >> 12) & 1; // 13-й бит (индексация с 0)
    if (stSignState)
    {
            // Ремонт - высший приоритет
            warDiag.visible("true");
            warDiag.fill("[pattern,[fit,any,repairModIzm.svg]]");
        }
        else if (!value[2])
        {
            // Диагностика связи - средний приоритет
            warDiag.visible("true");
            warDiag.fill("[pattern,[fit,any,diagWarningV1.svg]]");
        }
        else
        {
            // Нормальное состояние - скрыть warDiag
            warDiag.visible("false");
        }
  //   DebugN((value1) || (value2));
    if (value[3])
    {
      backolDI.backCol("SKIFDiagWarmingDyn");
      forecolDI.foreCol("Black");
    }
    else
    {
      backolDI.backCol("SKIFDiDefault");
      forecolDI.foreCol("SKIFDiagWarning");
    }
  }
//------------------------------------------------------------------------------------------------------------------//
  public void updateStateTitle(mapping settings)
  {
    title_tag.toolTipText(dpGetDescription(dpSubStr(settings["dpName"], DPSUB_DP)+ "."));
    dpConnect("updateStateTitleCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static void updateStateTitleCB(string dpe, bool value)
  {
    if (value)
    {
      title_tag.foreCol(actColorText);
      BacolDI.backCol("White");
    }
    else
    {
      title_tag.foreCol("SKIFDiDefault");
      BacolDI.backCol("_3DFace");
    }
  }
//------------------------------------------------------------------------------------------------------------------//
  public void updateStateSong(mapping settings)
  {
    dpConnect("updateStateSongCB", settings["dpName"] + ".State.TimP:_online.._value");
    BacolDI.toolTipText(dpGetDescription(dpSubStr(settings["dpName"],DPSUB_DP)+ "."));
  }

  public static void updateStateSongCB(string dpe1, bool value1)
  {
    if (value1)
    {
      RECTANGLE_ACT.visible(TRUE);
    }
    else{
      RECTANGLE_ACT.visible(FALSE);
    }
  }
//------------------------------------------------------------------------------------------------------------------//
  public void updateStateFire(mapping settings)
  {
    dpConnect("updateStateFireCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateFireCB(string dpName, bool value)
  {
    switch(value)
    {
      case 1:
      {
        setValueLib("title_tag", "visible", TRUE);
        setValueLib("back", "visible", TRUE);
        break;
      }
      default:
      {
        setValueLib("title_tag", "visible", FALSE);
        setValueLib("back", "visible", FALSE);
      }
    }
  }
//------------------------------------------------------------------------------------------------------------------//
  public void updateStateReceipt(mapping settings)
  {
    bacolDI.toolTipText(dpGetDescription(dpSubStr(settings["dpName"],DPSUB_DP)+ "."));
//     dpConnect("updateStateReceiptCB", settings["dpName"] + ".State.TimP:_online.._value",
//                                       settings["dpName"] + ".State.TimP:_alert_hdl.._ack_possible");
    dpConnect("updateStateReceiptCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static void updateStateReceiptCB(string dpe1, bool value1)
  {
  //   DebugN((value1) || (value2));
    if (value1)
    {
      RECTANGLE_NOT.visible(FALSE);
      backolDI.foreCol("SKIFObjTitleDefault");
    }
    else
    {
      RECTANGLE_NOT.visible(TRUE);
      backolDI.foreCol(backolDI.backCol());
    }
  }


//------------------------------------------------------------------------------------------------------------------//
  public void updateStateVent(mapping settings)
  {
    dpConnect("updateStateVentCB", settings["dpName"] + ".State.TimP:_online.._value");
        tag.text(UpdateName(settings["dpName"]));

  }

  public static updateStateVentCB(string dpName, bool value)
  {
    switch(value)
    {
      case 1:
      {
        setValueLib("state1", "backCol", "green");
        setValueLib("state2", "backCol", "green");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
      }
      default:
      {
        setValueLib("state1", "backCol", "yellow");
        setValueLib("state2", "backCol", "yellow");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
      }
    }
  }
//------------------------------------------------------------------------------------------------------------------//
  public void updateStateVentInvert(mapping settings)
  {
    dpConnect("updateStateVentInvertCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateVentInvertCB(string dpName, bool value)
  {
    switch(value)
    {
      case 0:
      {
        setValueLib("state1", "backCol", "green");
        setValueLib("state2", "backCol", "green");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
      }
      default:
      {
        setValueLib("state1", "backCol", "yellow");
        setValueLib("state2", "backCol", "yellow");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
      }
    }
  }
//------------------------------------------------------------------------------------------------------------------//

};

class DI_rs:skifcontent
{
  public void changeState(string obj, string col)
  {
    setValueLib(obj + ".reg1", "backCol", col);
  }

};

class TAIRA_PP:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value",
                               settings["dpName"] + ".ValuePV:_online.._value");
    tag.text(UpdateName(settings["dpName"]));
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
    setValueLib("valuePV", "text", value[2]);

    switch(value[1])
    {
      case 1:
        setValueLib("ppState", "backCol", "red");
        setValueLib("fanBlades1", "color", "black");
        setValueLib("fanBlades2", "color", "_Transparent");
        break;
      case 2:
        setValueLib("ppState", "backCol", "greenDynWhite");
        setValueLib("fanBlades1", "color", "blackDynTransparent");
        setValueLib("fanBlades2", "color", "blackDynTransparentRev");
        break;
      case 3:
        setValueLib("ppState", "backCol", "green");
        setValueLib("fanBlades1", "color", "blackDynTransparent");
        setValueLib("fanBlades2", "color", "blackDynTransparentRev");
        break;
      case 4:
        setValueLib("ppState", "backCol", "yellowDynWhite");
        setValueLib("fanBlades1", "color", "blackDynTransparent");
        setValueLib("fanBlades2", "color", "blackDynTransparentRev");
        break;
      case 5:
        setValueLib("ppState", "backCol", "yellow");
        setValueLib("fanBlades1", "color", "black");
        setValueLib("fanBlades2", "color", "_Transparent");
        break;
    }
  }


};

class TAIRA_PUMP:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value");
    tag.text(UpdateName(settings["dpName"]));
  }

  public static updateStateCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
        setValueLib("pumpState", "backCol", "red");
        break;
      case 2:
        setValueLib("pumpState", "backCol", "greenDynWhite");
        break;
      case 3:
        setValueLib("pumpState", "backCol", "green");
        break;
      case 4:
        setValueLib("pumpState", "backCol", "yellowDynWhite");
        break;
      case 5:
        setValueLib("pumpState", "backCol", "yellow");
        break;
    }
  }
  //Скрипт СТЕПА. Переименовал имя скрипта. В объектах тоже
  public void updateModeStep(mapping settings){
    dpConnect("updateModeStepCB", settings["dpName"] + ".mode.auto:_online.._value",
                              settings["dpName"] + ".mode.manual:_online.._value");
  }

  public static updateModeStepCB(dyn_string dpName, dyn_bool value){
    if(!value[1] && !value[2]){
      setValueLib("auto", "visible", false);
      setValueLib("manual", "visible", false);
    }
    else if(!value[1] && value[2]){
      setValueLib("auto", "visible", false);
      setValueLib("manual", "visible", true);
    }
    else{
      setValueLib("auto", "visible", true);
      setValueLib("manual", "visible", false);
    }
  }

//Временное решение для режима работы 21.05.2025 Максим
  public static updateModeCB(string dpAutoMode,bool valueAutoMode,string dpManualMode, bool valueManualMode)
  {
    DebugN("valueAutoMode",valueAutoMode,"valueManualMode",valueManualMode);
    if((valueAutoMode && valueManualMode) || (!valueAutoMode && !valueManualMode))
      setValueLib("pumpMode", "visible", false);
    else if(valueAutoMode)
    {
      setValueLib("pumpMode","text","А");
      setValueLib("pumpMode","foreCol","{77,111,57}");
      setValueLib("pumpMode","visible", true);
    }
    else if(valueManualMode)
    {
      setValueLib("pumpMode","text","Р");
      setValueLib("pumpMode","foreCol","STD_tendency_falling");
      setValueLib("pumpMode","visible", true);
    }
  }

  public void updateMode(mapping settings)
  {
    if(dpExists(settings["dpName"] + ".mode.auto") && dpExists(settings["dpName"] + ".mode.manual"))
    {
      DebugN("dp auto exists",dpExists(settings["dpName"] + ".mode.auto"),"dp manual exists",dpExists(settings["dpName"] + ".mode.manual"));
      dpConnect("updateModeCB", settings["dpName"] + ".mode.auto:_original.._value",
                                settings["dpName"] + ".mode.manual:_original.._value");
    }
    else
      setValueLib("pumpState", "visible", false);
  }
//Временное решение для режима работы 21.05.2025 Максим

  public void updateStatePV(mapping settings)
  {
    dpConnect("updateStateCBPV", settings["dpName"] + ".State:_online.._value",
                               settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCBPV(dyn_string dpName, dyn_anytype value)
  {
    switch(value[1])
    {
      case 1:
        setValueLib("pumpState", "backCol", "red");
        break;
      case 2:
        setValueLib("pumpState", "backCol", "greenDynWhite");
        break;
      case 3:
        setValueLib("pumpState", "backCol", "green");
        break;
      case 4:
        setValueLib("pumpState", "backCol", "yellowDynWhite");
        break;
      case 5:
        setValueLib("pumpState", "backCol", "yellow");
        break;
    }
     float val = value[2];
     string visualVal = val;
     if(val - floor(val) > 0){
       sprintf(visualVal,"%.0f",val);
     }
     setValueLib("valuePV", "text", visualVal);
     string HaveUnit = dpGetUnit(dpName[2]);

    if (HaveUnit == "") {
    setValueLib("unit", "text" , "???");
  } else {
    setValueLib("unit", "text", HaveUnit);
  }
  }
};

class TAIRA_PUMP_PV:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value",
                               settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
    switch(value[1])
    {
      case 1:
        setValueLib("pumpState", "backCol", "red");
        break;
      case 2:
        setValueLib("pumpState", "backCol", "greenDynWhite");
        break;
      case 3:
        setValueLib("pumpState", "backCol", "green");
        break;
      case 4:
        setValueLib("pumpState", "backCol", "yellowDynWhite");
        break;
      case 5:
        setValueLib("pumpState", "backCol", "yellow");
        break;
    }
     setValueLib("valuePV", "text", value[2]);
     string HaveUnit = dpGetUnit(dpName[2]);

    if (HaveUnit == "") {
    setValueLib("unit", "text" , "???");
  } else {
    setValueLib("unit", "text", HaveUnit);
  }
  }
};

/*
  Поделил каждую "папку" на отдельные функции.
  Необходимо это для того, чтобы упростить dpConnect и
  была возможность включать/отключать определенные компоненты
  вент. системы
*/
class TAIRA_VENT_SYS:skifcontent{
  public void updateVentSys(mapping settings){
    //обработчик состояний
    dpConnect("updateStateCB", settings["dpName"] + ".state.emergency:_online.._value",
                               settings["dpName"] + ".state.start:_online.._value",
                               settings["dpName"] + ".state.stop:_online.._value",
                               settings["dpName"] + ".state.starting:_online.._value",
                               settings["dpName"] + ".state.stoping:_online.._value");
    //обработчик ошибок
    dpConnect("updateErrorCB", settings["dpName"] + ".error.sensorBreak:_online.._value",
                               settings["dpName"] + ".error.errorZdHeater:_online.._value",
                               settings["dpName"] + ".error.errorZdChiller:_online.._value",
                               settings["dpName"] + ".error.errorVzzd:_online.._value",
                               settings["dpName"] + ".error.warningFreeze:_online.._value",
                               settings["dpName"] + ".error.errorFilter:_online.._value",
                               settings["dpName"] + ".error.autoSwitchPV:_online.._value",
                               settings["dpName"] + ".error.autoSwitchVV:_online.._value",
                               settings["dpName"] + ".error.autoSwitchPP:_online.._value");
    //обработчик сезонов
    dpConnect("updateSeasonCB", settings["dpName"] + ".season.winter:_online.._value",
                                settings["dpName"] + ".season.summer:_online.._value",
                                settings["dpName"] + ".season.auto:_online.._value");

    //обработчик режимов
    dpConnect("updateModeCB", settings["dpName"] + ".mode.manual:_online.._value",
                              settings["dpName"] + ".mode.distance:_online.._value");
  }

  public static updateStateCB(dyn_string dps, dyn_bool values){
    int state = 0;

    //перекидываем биты в инт, чтобы было можно свичем менять состояния(так код красивее)
    //так же для свитч стоймость для доп условия меньше и код работает на микросекунды быстрее =)
    //1,2,4,8,16 соответственно
    state = (values[1] << 0) | (values[2] << 1) | (values[3] << 2) | (values[4] << 3) | (values[5] << 4);
    switch(state){
          case 1:
            setValueLib("state1", "backCol", "red");
            break;
          case 2:
            setValueLib("state1", "backCol", "green");
            break;
          case 4:
            setValueLib("state1", "backCol", "yellow");
            break;
          case 8:
            setValueLib("state1", "backCol", "greenDynWhite");
            break;
          case 16:
            setValueLib("state1", "backCol", "yellowDynWhite");
            break;
          default:{
              setValueLib("state1", "backCol", "{183,184,187}"); //неопределенное состояния, когда возведено несколько битов(или ни одного)

              /*
              Если получить остаток от числа при делении на 2 и значение нечетное, то остаток будет
              равен 1. Если остаток равен 1, то первый бит аварии возведен в положение true. Выводить
              аварию нужно в любом случае. В ином случае состояние оставляем "неопределенным"
              */
              if((state % 2) == 1){
                setValueLib("state1", "backCol", "red");
              }
            }
            break;
    }
  }

  public static updateSeasonCB(dyn_string dps, dyn_bool values){
    int season = 0;
    season = (values[1] << 0) | (values[2] << 1) | (values[3] << 2);

    switch(season){
      case 1:{
          setValueLib("SEASON_TEXT", "text", "ЗИМА");
          setValueLib("SEASON_TEXT", "foreCol", "blue");
        } break;
      case 2:{
          setValueLib("SEASON_TEXT", "text", "ЛЕТО");
          setValueLib("SEASON_TEXT", "foreCol", "{38,157,44}");
        } break;
      case 4:{
          setValueLib("SEASON_TEXT", "text", "АВТО");
          setValueLib("SEASON_TEXT", "foreCol", "black");
        } break;
        default:{
          setValueLib("SEASON_TEXT", "text", "НЕОПРЕД.");
          setValueLib("SEASON_TEXT", "foreCol", "WF_Text");
        } break;

    }
  }

  public static updateModeCB(dyn_string dps, dyn_bool values){
    int mode = 0;

    mode = (values[1] << 0) | (values[2] << 1);


    switch(mode){
      case 1:{
          setValueLib("MODE_TEXT", "text", "Мест.");
          setValueLib("MODE_TEXT", "foreCol", "black");
        } break;
        case 2:{
          setValueLib("MODE_TEXT", "text", "Дист.");
          setValueLib("MODE_TEXT", "foreCol", "blue");
        } break;
          default:{
          setValueLib("MODE_TEXT", "text", "НЕОПРЕД.");
          setValueLib("MODE_TEXT", "foreCol", "WF_Text");
        }
    }
  }

};


class TAIRA_VENT:skifcontent
{
  public void updateState(mapping settings)
  {
//     dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value",
//                                settings["dpName"] + ".ValuePV:_online.._value");

      dpConnect("updateStateCB",       settings["dpName"] + ".ValuePV:_online.._value",
                                       settings["dpName"] + ".state.emergency:_online.._value",
                                       settings["dpName"] + ".state.starting:_online.._value",
                                       settings["dpName"] + ".state.start:_online.._value",
                                       settings["dpName"] + ".state.stoping:_online.._value",
                                       settings["dpName"] + ".state.stop:_online.._value");
    tag.text(UpdateName(settings["dpName"]));
  }

  public void updateStateEdit(mapping settings)
  {
    dpConnect("updateStateEditCB",     settings["dpName"] + ".state.emergency:_online.._value",
                                       settings["dpName"] + ".state.starting:_online.._value",
                                       settings["dpName"] + ".state.start:_online.._value",
                                       settings["dpName"] + ".state.stoping:_online.._value",
                                       settings["dpName"] + ".state.stop:_online.._value",
                                       settings["dpName"] + ".Mode:_online.._value",
                                       settings["dpName"] + ".ValuePV:_online.._value");

    tag.text(UpdateName(settings["dpName"]));
  }
  public void updateStateSystemSimp(mapping settings){
//    dpConnect("updateStateSystemSimpCB", settings["dpName"] + ".State:_online.._value");
      dpConnect("updateStateSystemSimpCB", settings["dpName"] + ".state.emergency:_online.._value",
                                           settings["dpName"] + ".state.starting:_online.._value",
                                           settings["dpName"] + ".state.start:_online.._value",
                                           settings["dpName"] + ".state.stoping:_online.._value",
                                           settings["dpName"] + ".state.stop:_online.._value");
  }

  public void updateStateSystem(mapping settings){
//    dpConnect("updateStateSystemCB", settings["dpName"] + ".State:_online.._value");
      dpConnect("updateStateSystemCB", settings["dpName"] + ".state.emergency:_online.._value",
                                       settings["dpName"] + ".state.starting:_online.._value",
                                       settings["dpName"] + ".state.start:_online.._value",
                                       settings["dpName"] + ".state.stoping:_online.._value",
                                       settings["dpName"] + ".state.stop:_online.._value");
          tag.text(UpdateName(settings["dpName"]));

  }

  public void updateStateMode(mapping settings){
    dpConnect("updateStateModeCB", settings["dpName"] + ".State:_online.._value",
                                   settings["dpName"] + ".Mode:_online.._value");
  }

  public static updateStateModeCB(dyn_string dpName, dyn_anytype value){

    switch(value[1]){
      case 1: setValueLib("state1", "backCol", "red"); break;
      case 2: setValueLib("state1", "backCol", "greenDynWhite");break;
      case 3: setValueLib("state1", "backCol", "green");break;
      case 4: setValueLib("state1", "backCol", "yellowDynWhite");break;
      case 5: setValueLib("state1", "backCol", "yellow");break;
      default: setValueLib("state1", "backCol", "grey");break;
    }

    switch(value[2]){
      case 1: setValueLib("MODE_TEXT", "text", "Р"); setValueLib("MODE_TEXT", "foreCol", "blue"); break;
      case 2: setValueLib("MODE_TEXT", "text", "М"); setValueLib("MODE_TEXT", "foreCol", "blue"); break;
      case 3: setValueLib("MODE_TEXT", "text", "Д"); setValueLib("MODE_TEXT", "foreCol", "normAI"); break;
      case 4: setValueLib("MODE_TEXT", "text", "А"); setValueLib("MODE_TEXT", "foreCol", "normAI"); break;
      default: setValueLib("MODE_TEXT", "text", ""); break;
    }



  }

  public static updateStateEditCB(dyn_string dpName, dyn_anytype value){
    setValueLib("valuePV", "text", value[7]);
    switch(VentState(dpName,value))
    {
      case 1:
        setValueLib("state1", "backCol", "red");
        setValueLib("state2", "backCol", "red");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
      case 2:
        setValueLib("state1", "backCol", "greenDynWhite");
        setValueLib("state2", "backCol", "greenDynWhite");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 3:
        setValueLib("state1", "backCol", "green");
        setValueLib("state2", "backCol", "green");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 4:
        setValueLib("state1", "backCol", "yellowDynWhite");
        setValueLib("state2", "backCol", "yellowDynWhite");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 5:
        setValueLib("state1", "backCol", "yellow");
        setValueLib("state2", "backCol", "yellow");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
    }

    switch(value[6]){
      case 1: setValueLib("MODE_TEXT", "text", "Р"); setValueLib("MODE_TEXT", "foreCol", "blue"); break;
      case 2: setValueLib("MODE_TEXT", "text", "М"); setValueLib("MODE_TEXT", "foreCol", "blue"); break;
      case 3: setValueLib("MODE_TEXT", "text", "Д"); setValueLib("MODE_TEXT", "foreCol", "normAI"); break;
      case 4: setValueLib("MODE_TEXT", "text", "А"); setValueLib("MODE_TEXT", "foreCol", "normAI"); break;
      default: setValueLib("MODE_TEXT", "text", ""); break;
    }



  }

  public static updateStateSystemSimpCB(dyn_string dpName, dyn_anytype value){
    switch(VentState(dpName,value)){
      case 1:
        setValueLib("state1", "backCol", "red");
        break;
      case 2:
        setValueLib("state1", "backCol", "greenDynWhite");
        break;
      case 3:
        setValueLib("state1", "backCol", "green");
        break;
      case 4:
        setValueLib("state1", "backCol", "yellowDynWhite");
        break;
      case 5:
        setValueLib("state1", "backCol", "yellow");
        break;
      default:
        setValueLib("state1", "backCol", "SBISMessageBack");
        break;
    }

  }

  public static updateStateSystemCB(dyn_string dpName, dyn_anytype value){
    switch(VentState(dpName,value)){
      case 1:
        setValueLib("state1", "backCol", "red");
        setValueLib("state2", "backCol", "red");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
      case 2:
        setValueLib("state1", "backCol", "greenDynWhite");
        setValueLib("state2", "backCol", "greenDynWhite");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 3:
        setValueLib("state1", "backCol", "green");
        setValueLib("state2", "backCol", "green");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 4:
        setValueLib("state1", "backCol", "yellowDynWhite");
        setValueLib("state2", "backCol", "yellowDynWhite");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 5:
        setValueLib("state1", "backCol", "yellow");
        setValueLib("state2", "backCol", "yellow");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
    }

  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
    setValueLib("valuePV", "text", value[1]);
    switch(VentState(dpName,value))
    {
      case 1:
        setValueLib("state1", "backCol", "red");
        setValueLib("state2", "backCol", "red");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
      case 2:
        setValueLib("state1", "backCol", "greenDynWhite");
        setValueLib("state2", "backCol", "greenDynWhite");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 3:
        setValueLib("state1", "backCol", "green");
        setValueLib("state2", "backCol", "green");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 4:
        setValueLib("state1", "backCol", "yellowDynWhite");
        setValueLib("state2", "backCol", "yellowDynWhite");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 5:
        setValueLib("state1", "backCol", "yellow");
        setValueLib("state2", "backCol", "yellow");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
    }
  }

public static updateStateCBFps(dyn_anytype dpName,dyn_anytype value)
{
  DebugN(dpName);DebugN(value);
  switch(VentState(dpName,value))
    {
       case 0:
      setValueLib  ("stateTxt","text","Не определено");
      setValueLib  ("state1","backCol","SKIFDiDefault");
      setValueLib  ("state2","backCol","SKIFDiDefault");
        break;
      case 1:
      setValueLib  ("stateTxt","text","СБОЙ");
      setValueLib  ("state1","backCol","red");
      setValueLib  ("state2","backCol","red");
        break;
      case 2:
       setValueLib ("stateTxt","text","ЗАПУСКАЕТСЯ");
       setValueLib ("state1","backCol","greenDynWhite");
       setValueLib ("state2","backCol","greenDynWhite");
        break;
      case 3:
       setValueLib ("stateTxt","text","ЗАПУЩЕН");
       setValueLib ("state1","backCol","green");
       setValueLib ("state2","backCol","green");
        break;
      case 4:
       setValueLib ("stateTxt","text","ОСТАНАВЛИВАЕТСЯ");
       setValueLib ("state1","backCol","yellowDynWhite");
       setValueLib ("state2","backCol","yellowDynWhite");
        break;
      case 5:
       setValueLib ("stateTxt","text","ОСТАНОВЛЕН");
       setValueLib ("state1","backCol","yellow");
       setValueLib ("state2","backCol","yellow");
        break;
//       case 6:
//         stateTxt.text("ГОТОВ");
//         state1.backCol("ready");
//         state2.backCol("ready");
//         break;
      }
}

};

class TAIRA_ZD:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value",
                               settings["dpName"] + ".ValuePV:_online.._value");
    tag.text(UpdateName(settings["dpName"]));
  }

  public void updateStateNoPv(mapping settings)
  {
    dpConnect("updateStateNoPvCB", settings["dpName"] + ".State:_online.._value");
        tag.text(UpdateName(settings["dpName"]));
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
    setValueLib("valuePV", "text", value[2]);

    switch(value[1])
    {
      case 3:
        setValueLib("top", "backCol", "red");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
        setValueLib("bottom", "backCol", "yellow");
        break;
      case 2:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
        setValueLib("bottom", "backCol", "yellow");
        break;
      case 1:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "green");
        setValueLib("left", "backCol", "green");
        setValueLib("bottom", "backCol", "green");
        break;
       case 4:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "green");
        setValueLib("bottom", "backCol", "yellow");
        break;
       default:
        setValueLib("top", "backCol", "SBISMessageBack");
        setValueLib("right", "backCol", "SBISMessageBack");
        setValueLib("left", "backCol", "SBISMessageBack");
        setValueLib("bottom", "backCol", "SBISMessageBack");
    }
  }

  public static updateStateNoPvCB(string dpName, int iState)
  {
    switch(iState)
    {
      case 3:
        setValueLib("top", "backCol", "red");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
        setValueLib("bottom", "backCol", "yellow");
        break;
      case 2:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
        setValueLib("bottom", "backCol", "yellow");
        break;
      case 1:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "green");
        setValueLib("left", "backCol", "green");
        setValueLib("bottom", "backCol", "green");
        break;
       case 4:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "green");
        setValueLib("bottom", "backCol", "yellow");
        break;
       default:
        setValueLib("top", "backCol", "SBISMessageBack");
        setValueLib("right", "backCol", "SBISMessageBack");
        setValueLib("left", "backCol", "SBISMessageBack");
        setValueLib("bottom", "backCol", "SBISMessageBack");
    }
  }

  public void updateStateSimp(mapping settings){
    dpConnect("updateStateSimpCB", settings["dpName"] + ".State:_online.._value");
  }

  public static updateStateSimpCB(string dpName, anytype value){
    switch(value){
      case 1:
        setValueLib("state1", "backCol", "green"); break;
      case 2:
        setValueLib("state1", "backCol", "yellow"); break;
      case 3:
        setValueLib("state1", "backCol", "red"); break;
      default:
        setValueLib("state1", "backCol", "SBISMessageBack"); break;

    }
  }

  public void updateStateVert(mapping settings)
  {
    dpConnect("updateStateCBVert", settings["dpName"] + ".State:_online.._value",
                               settings["dpName"] + ".ValuePV:_online.._value");
    tag.text(UpdateName(settings["dpName"]));
  }

  public static updateStateCBVert(dyn_string dpName, dyn_anytype value)
  {
    setValueLib("valuePV", "text", value[2]);

    switch(value[1])
    {
      case 3:
        setValueLib("top", "backCol", "red");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
        break;
      case 2:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
        break;
      case 1:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "green");
        setValueLib("left", "backCol", "green");
        break;
       case 4:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "green");
        break;
       default:
        setValueLib("top", "backCol", "SBISMessageBack");
        setValueLib("right", "backCol", "SBISMessageBack");
        setValueLib("left", "backCol", "SBISMessageBack");
    }
  }

  public void updateStateHoriz(mapping settings)
  {
    dpConnect("updateStateCBHoriz", settings["dpName"] + ".State:_online.._value",
                               settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCBHoriz(dyn_string dpName, dyn_anytype value)
  {
    setValueLib("valuePV", "text", value[2]);

    switch(value[1])
    {
      case 3:
        setValueLib("top", "backCol", "red");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
        break;
      case 2:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
        break;
      case 1:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "green");
        setValueLib("left", "backCol", "green");
        break;
       case 4:
        setValueLib("top", "backCol", "green");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "green");
        break;
       default:
        setValueLib("top", "backCol", "SBISMessageBack");
        setValueLib("right", "backCol", "SBISMessageBack");
        setValueLib("left", "backCol", "SBISMessageBack");
    }
  }
};

class TAIRA_Electric_heater:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value");
  }

  public void updateStateSimp(mapping settings)
  {
    dpConnect("updateStateSimpCB", settings["dpName"] + ".State:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
    switch(value[1])
    {
      case 3:
        setValueLib("back", "backCol", "red");
        break;
      case 2:
        setValueLib("back", "backCol", "yellow");
        break;
      case 1:
        setValueLib("back", "backCol", "green");
        break;
       default:
        setValueLib("back", "backCol", "SBISMessageBack");
    }
  }

  public static updateStateSimpCB(dyn_string dpName, dyn_anytype value)
  {
    switch(value[1])
    {
      case 3:
        setValueLib("state1", "backCol", "red");
        break;
      case 2:
        setValueLib("state1", "backCol", "yellow");
        break;
      case 1:
        setValueLib("state1", "backCol", "green");
        break;
       default:
        setValueLib("state1", "backCol", "SBISMessageBack");
    }
  }
};

class TAIRA_VENT_Double:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"][1] + ".state.emergency:_online.._value",
			       settings["dpName"][1] + ".state.starting:_online.._value",
			       settings["dpName"][1] + ".state.start:_online.._value",
			       settings["dpName"][1] + ".state.stoping:_online.._value",
			       settings["dpName"][1] + ".state.stop:_online.._value",
                               settings["dpName"][1] + ".ValuePV:_online.._value",
                                settings["dpName"][2] + ".state.emergency:_online.._value",
				settings["dpName"][2] + ".state.starting:_online.._value",
				settings["dpName"][2] + ".state.start:_online.._value",
				settings["dpName"][2] + ".state.stoping:_online.._value",
				settings["dpName"][2] + ".state.stop:_online.._value",
                                settings["dpName"][2] + ".ValuePV:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
    setValueLib("valuePV1", "text", value[6]);
    setValueLib("valuePV2", "text", value[12]);

    int minState;
    dyn_anytype Temp;
    dyn_anytype TempDp;
    dynAppend(Temp,value[1]);dynAppend(Temp,value[2]);dynAppend(Temp,value[3]);dynAppend(Temp,value[4]);dynAppend(Temp,value[5]);
    dynAppend(TempDp,dpName[1]);dynAppend(TempDp,dpName[2]);dynAppend(TempDp,dpName[3]);dynAppend(TempDp,dpName[4]);dynAppend(TempDp,dpName[5]);
    int val1 = VentState(TempDp,Temp);
    dynClear(Temp);dynAppend(Temp,value[7]);dynAppend(Temp,value[8]);dynAppend(Temp,value[9]);dynAppend(Temp,value[10]);dynAppend(Temp,value[11]);
    dynClear(TempDp);dynAppend(TempDp,dpName[7]);dynAppend(TempDp,dpName[8]);dynAppend(TempDp,dpName[9]);dynAppend(TempDp,dpName[10]);dynAppend(TempDp,dpName[11]);
    int val2 = VentState(TempDp,Temp);

    if (val1 <= val2)
        minState = val1;
    else
        minState = val2;

    switch(minState)
    {
      case 1:
        setValueLib("state1", "backCol", "red");
        setValueLib("state2", "backCol", "red");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
      case 2:
        setValueLib("state1", "backCol", "greenDynWhite");
        setValueLib("state2", "backCol", "greenDynWhite");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 3:
        setValueLib("state1", "backCol", "green");
        setValueLib("state2", "backCol", "green");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 4:
        setValueLib("state1", "backCol", "yellowDynWhite");
        setValueLib("state2", "backCol", "yellowDynWhite");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
        break;
      case 5:
        setValueLib("state1", "backCol", "yellow");
        setValueLib("state2", "backCol", "yellow");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        break;
    }


    switch(val1)
    {
      case 1:
        setValueLib("MOTOR1", "color", "red");
        break;
      case 2:
        setValueLib("MOTOR1", "color", "greenDynWhite");
        break;
      case 3:
        setValueLib("MOTOR1", "color", "green");
        break;
      case 4:
        setValueLib("MOTOR1", "color", "yellowDynWhite");
        break;
      case 5:
        setValueLib("MOTOR1", "color", "yellow");
        break;
    }

    switch(val2)
    {
      case 1:
        setValueLib("MOTOR2", "color", "red");
        break;
      case 2:
        setValueLib("MOTOR2", "color", "greenDynWhite");
        break;
      case 3:
        setValueLib("MOTOR2", "color", "green");
        break;
      case 4:
        setValueLib("MOTOR2", "color", "yellowDynWhite");
        break;
      case 5:
        setValueLib("MOTOR2", "color", "yellow");
        break;
    }
  }

};

class TAIRA_Electric_heater_PNR:TAIRA_Electric_heater
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
    switch(value[1])
    {
      case 3:
        setValueLib("back", "backCol", "blue");
        break;
      case 2:
        setValueLib("back", "backCol", "pink");
        break;
      case 1:
        setValueLib("back", "backCol", "white");
        break;
       default:
        setValueLib("back", "backCol", "SBISMessageBack");
    }
  }
};

class TAIRA_VZZD:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value");
        tag.text(UpdateName(settings["dpName"]));

  }

  public static updateStateCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
        setValueLib("vzzdState", "backCol", "green");
        setValueLib("open1", "visible", "true");
        setValueLib("open2", "visible", "true");
        setValueLib("open3", "visible", "true");
        setValueLib("close", "visible", "false");
        break;
      case 2:
        setValueLib("vzzdState", "backCol", "yellow");
        setValueLib("open1", "visible", "false");
        setValueLib("open2", "visible", "false");
        setValueLib("open3", "visible", "false");
        setValueLib("close", "visible", "true");
        break;
      default:
        setValueLib("vzzdState", "backCol", "SBISMessageBack");
        setValueLib("close", "visible", "false");
        setValueLib("open1", "visible", "false");
        setValueLib("open2", "visible", "false");
        setValueLib("open3", "visible", "false");
        break;
    }
  }

  public void updateStateR(mapping settings)
  {
    dpConnect("updateStateRCB", settings["dpName"] + ".State:_online.._value");
    tag.text(UpdateName(settings["dpName"]));
  }

  public static updateStateRCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
        setValueLib("vzzdState", "backCol", "green");
        setValueLib("open1", "visible", "false");
        setValueLib("open2", "visible", "false");
        setValueLib("open3", "visible", "false");
        setValueLib("close", "visible", "true");
        break;
      case 2:
        setValueLib("vzzdState", "backCol", "yellow");
        setValueLib("open1", "visible", "true");
        setValueLib("open2", "visible", "true");
        setValueLib("open3", "visible", "true");
        setValueLib("close", "visible", "false");
        break;
      default:
        setValueLib("vzzdState", "backCol", "SBISMessageBack");
        setValueLib("close", "visible", "false");
        setValueLib("open1", "visible", "false");
        setValueLib("open2", "visible", "false");
        setValueLib("open3", "visible", "false");
        break;
    }
  }


  public void updateStatePV(mapping settings)
  {
    dpConnect("updateStateCBPV", settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCBPV(string dpName, int value)
  {
    switch(value)
    {
      case 0: setValueLib("vzzdState", "backCol", "yellow"); break;
//       case 100:  setValueLib("vzzdState", "backCol", "green"); break;
      default: setValueLib("vzzdState", "backCol", "green"); break;
    }
    setValueLib("valuePV", "text", value);
    float newVal = value * 90 / 100 * -1;
    setValueLib("open1", "rotation", newVal);
    setValueLib("open2", "rotation", newVal);
    setValueLib("open3", "rotation", newVal);
  }

  public void updateStateReverse(mapping settings)
  {
    dpConnect("updateStateCBReverse", settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCBReverse(string dpName, int value)
  {
    switch(value)
    {
      case 0: setValueLib("vzzdState", "backCol", "yellow"); break;
      default:setValueLib("vzzdState", "backCol", "green"); break;
    }
    setValueLib("valuePV", "text", value);
    float newVal = value * 90 / 100;
    setValueLib("open1", "rotation", newVal - 90);
    setValueLib("open2", "rotation", newVal - 90);
    setValueLib("open3", "rotation", newVal - 90);
  }
};

class TAIRA_VZZD_PV_Horiz:skifcontent{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCB(string dpName, int value)
  {
    switch(value)
    {
      case 0: setValueLib("vzzdState", "backCol", "yellow"); break;
      default: setValueLib("vzzdState", "backCol", "green"); break;
    }
    setValueLib("valuePV", "text", value);
    float newVal = value * 90 / 100 * (-1);
    setValueLib("open1", "rotation", newVal);
    setValueLib("open2", "rotation", newVal);
    setValueLib("open3", "rotation", newVal);
  }
};

class TAIRA_VZZDR:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value");
        tag.text(UpdateName(settings["dpName"]));

  }

  public static updateStateCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
        setValueLib("vzzdState", "backCol", "green");
        setValueLib("open", "visible", "true");
        setValueLib("close", "visible", "false");
        break;
      case 2:
        setValueLib("vzzdState", "backCol", "yellow");
        setValueLib("open", "visible", "false");
        setValueLib("close", "visible", "true");
        break;
      default:
        setValueLib("vzzdState", "backCol", "SBISMessageBack");
        setValueLib("open", "visible", "false");
        setValueLib("closing1", "visible", "false");
        setValueLib("closing2", "visible", "false");
        setValueLib("closing3", "visible", "false");
        break;
    }
  }

  public void updateStateR(mapping settings)
  {
    dpConnect("updateStateRCB", settings["dpName"] + ".State:_online.._value");
        tag.text(UpdateName(settings["dpName"]));

  }

  public static updateStateRCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
        setValueLib("vzzdState", "backCol", "green");
        setValueLib("opening", "visible", "true");
        setValueLib("closing1", "visible", "false");
        setValueLib("closing2", "visible", "false");
        setValueLib("closing3", "visible", "false");
        break;
      case 2:
        setValueLib("vzzdState", "backCol", "yellow");
        setValueLib("opening", "visible", "false");
        setValueLib("closing1", "visible", "true");
        setValueLib("closing2", "visible", "true");
        setValueLib("closing3", "visible", "true");
        break;
      default:
        setValueLib("vzzdState", "backCol", "SBISMessageBack");
        setValueLib("opening", "visible", "false");
        setValueLib("closing1", "visible", "false");
        setValueLib("closing2", "visible", "false");
        setValueLib("closing3", "visible", "false");
        break;
    }
  }


  public void updateStatePV(mapping settings)
  {
    dpConnect("updateStateCBPV", settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCBPV(string dpName, int value)
  {
    switch(value)
    {
      case 0: setValueLib("vzzdState", "backCol", "yellow"); break;
//       case 100:  setValueLib("vzzdState", "backCol", "green"); break;
      default: setValueLib("vzzdState", "backCol", "green"); break;
    }
    setValueLib("valuePV", "text", value);
    float newVal = value * 90 / 100 * -1;
    setValueLib("open1", "rotation", newVal);
    setValueLib("open2", "rotation", newVal);
    setValueLib("open3", "rotation", newVal);
  }

  public void updateStateReverse(mapping settings)
  {
    dpConnect("updateStateCBReverse", settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCBReverse(string dpName, int value)
  {
    switch(value)
    {
      case 0: setValueLib("vzzdState", "backCol", "yellow"); break;
      default:setValueLib("vzzdState", "backCol", "green"); break;
    }
    setValueLib("valuePV", "text", value);
    float newVal = value * 90 / 100;
    setValueLib("open1", "rotation", newVal);
    setValueLib("open2", "rotation", newVal);
    setValueLib("open3", "rotation", newVal);
  }
};


// class TAIRA_VZZD_PV:skifcontent
// {
//   public void updateState(mapping settings)
//   {
//     dpConnect("updateStateCB", settings["dpName"] + ".ValuePV:_online.._value", settings["dpName"] + ".State:_online.._value");
//   }
//
//   public static updateStateCB(dyn_string dpName, dyn_string value)
//   {
//     switch(value[2])
//     {
//       case 1:
//         {
//           setValue("vzzdState", "backCol", "yellow");
//           setValue("close", "visible", true);
//           setValue("open", "visible", false);
//           setValue("opening", "visible", false);
//           break;
//         }
//       case 2:
//         {
//           setValue("vzzdState", "backCol", "green");
//           setValue("close", "visible", false);
//           setValue("open", "visible", true);
//           setValue("opening", "visible", false);
//           break;
//         }
//         case 3:
//         {
//           setValue("vzzdState", "backCol", "green");
//           setValue("close", "visible", false);
//           setValue("open", "visible", false);
//           setValue("opening", "visible", true);
//           break;
//         }
//
//       default:{
//         setValue("vzzdState", "backCol", "SBISMessageBack");
//         setValue("close", "visible", false);
//         setValue("open", "visible", false);
//         setValue("opening", "visible", false);
//         break;
//       }
//     }
//
//     setValue("valuePV", "text", value[1]);
//   }
// };

class TAIRA_VZZD_PV:skifcontent{
  public void updateStatePV(mapping settings)
  {
    dpConnect("updateStateCBPV", settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCBPV(string dpName, int value)
  {
    switch(value)
    {
      case 0: setValueLib("vzzdState", "backCol", "yellow"); break;
//       case 100:  setValueLib("vzzdState", "backCol", "green"); break;
      default: setValueLib("vzzdState", "backCol", "green"); break;
    }
    setValueLib("valuePV", "text", value);
    float newVal = value * 90 / 100 * -1;
    setValueLib("open1", "rotation", newVal);
    setValueLib("open2", "rotation", newVal);
    setValueLib("open3", "rotation", newVal);
  }

  public void updateStateReverse(mapping settings)
  {
    dpConnect("updateStateCBReverse", settings["dpName"] + ".ValuePV:_online.._value");
  }

  public static updateStateCBReverse(string dpName, int value)
  {
    switch(value)
    {
      case 0: setValueLib("vzzdState", "backCol", "yellow"); break;
      default:setValueLib("vzzdState", "backCol", "green"); break;
    }
    setValueLib("valuePV", "text", value);
    float newVal = value * 90 / 100;
    setValueLib("open1", "rotation", newVal);
    setValueLib("open2", "rotation", newVal);
    setValueLib("open3", "rotation", newVal);
  }
};


class TAIRA_DI:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State:_online.._value");
    tag.text(UpdateName(settings["dpName"]));
  }

  public static updateStateCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
        setValueLib("state", "backCol", "red");
        setValueLib("tag", "foreCol", "black");
        break;
      default:
        setValueLib("state", "backCol", "SBISBackFalse");
        setValueLib("tag", "foreCol", "SKIFDiDefault");
    }
  }

  public void updateStateText(mapping settings)
  {
    dpConnect("updateStateTextCB", settings["dpName"] + ".State:_online.._value");
  }

  public static updateStateTextCB(string dpName, bool value)
  {
    if(value){
      setValueLib("DIText2", "visible", false);
      setValueLib("DIText1", "visible", true);
    }
    else{
      setValueLib("DIText2", "visible", true);
      setValueLib("DIText1", "visible", false);
    }
  }



  public void updateStateHeater(mapping settings)
  {
    dpConnect("updateStateHeaterCB", settings["dpName"] + ".State:_online.._value");
  }

  public static updateStateHeaterCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
        setValueLib("state", "visible", "true");
        break;
      default:
        setValueLib("state", "visible", "false");
    }
  }


  public void updateStateTerm(mapping settings)
  {
    dpConnect("updateStateTermCB", settings["dpName"] + ".State:_online.._value");
  }

  public static updateStateTermCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
        setValueLib("tag", "foreCol", "red");
        break;
      default:
        setValueLib("tag", "foreCol", "SKIFDiDefault");
    }
  }

  public void updateStateFire(mapping settings, string timp = "")
  {

		for (int i = 1; i <= dynlen(settings["dpName"]); i++)
			settings["dpName"][i] = settings["dpName"][i] + ".State" + timp + ":_online.._value";
		dpConnect("updateStateFireCB", settings["dpName"]);
//     dpConnect("updateStateFireCB", settings["dpName"] + ".State:_online.._value");
  }

  public static updateStateFireCB(dyn_string dpName, dyn_int value)
  {
		bool fire = false;
		for (int i = 1; i <= dynlen(value); i++)
			if (value[i]){
				fire = true;
				break;
			}

    switch(fire)
    {
      case 1:
      {
        setValueLib("tag", "visible", TRUE);
        setValueLib("title", "visible", TRUE);
        break;
      }
      default:
      {
        setValueLib("tag", "visible", FALSE);
        setValueLib("title", "visible", FALSE);
      }
    }
  }

  public void updateStateGreenYellow(mapping settings)
  {
    dpConnect("updateStateGreenYellowCB", settings["dpName"] + ".State:_online.._value");
  }

  public static updateStateGreenYellowCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
      {
        setValueLib("state", "backCol", "yellow");
//        setValue("tag", "foreCol", "yellow");
        break;
      }
      default:
      {
        setValueLib("state", "backCol", "{0,255,0}");
//        setValue("tag", "foreCol", "{0,255,0}");
      }
    }
  }
  public void updateStateGrayRed(mapping settings)
  {
    dpConnect("updateStateGrayRedCB", settings["dpName"] + ".State:_online.._value");
  }

  public static updateStateGrayRedCB(string dpName, int value)
  {
    switch(value)
    {
      case 1:
      {
        setValueLib("state", "backCol", "red");
//        setValue("tag", "foreCol", "yellow");
        break;
      }
      default:
      {
        setValueLib("state", "backCol", "_3DFace");
//        setValue("tag", "foreCol", "{0,255,0}");
      }
    }
  }
};


class TAIRA_AI:skifcontent
{
  public void updateState(mapping settings)
  { DebugN("mapping settings", settings);
    DebugN("mapping settings", settings["dpName"]);
    dpConnect("updateStateCB", settings["dpName"] + ".Value:_online.._value",
                               settings["dpName"] + ".state.emergLevel:_online.._value",
                               settings["dpName"] + ".state.warnLevel:_online.._value");

    tag.text(UpdateName(settings["dpName"]));

  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
		string val;
		sprintf(val, "%.1f", value[1]);
    bool invalid = dpName + ":_online.._invalid";
    string HaveUnit = dpGetUnit(dpName[1]);

    if (HaveUnit == "") {
    setValueLib("unit", "text" , "");
  } else {
    setValueLib("unit", "text", HaveUnit);
  }

    if (value[2])
      setValueLib("value", "foreCol", "red");
    else if (value[3])
      setValueLib("value", "foreCol", "yellow");
    else
      setValueLib("value", "foreCol", "normAI");

  if (false){
      setValueLib("value", "text", "___");
      setValueLib("value", "foreCol", "black");
    } else {
    setValueLib("value", "text", val);
    }
  }

    public void updateStateFlow(mapping settings)
  {
    dpConnect("updateStateCBFlow", settings["dpName"] + ".Value:_online.._value",
                               settings["dpName"] + ".state.emergLevel:_online.._value",
                               settings["dpName"] + ".state.warnLevel:_online.._value");
        tag.text(UpdateName(settings["dpName"]));

  }

  public static updateStateCBFlow(dyn_string dpName, dyn_anytype value)
  {
		string val;
		sprintf(val, "%.1f", value[1]);
    bool invalid = dpName + ":_online.._invalid";
    string HaveUnit = dpGetUnit(dpName[1]);

    if (HaveUnit == "") {
    setValueLib("unit", "text" , "");
  } else {
    setValueLib("unit", "text", HaveUnit);
  }

  setValueLib("value", "foreCol", "blue");

  if (false){
      setValueLib("value", "text", "___");
      setValueLib("value", "foreCol", "black");
    } else {
    setValueLib("value", "text", val);
    }
  }
};


class SCADTECH_DI:skifcontent{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateCB(string dpName, anytype value)
  {
    if(value)
    {
      setValueLib("DIText", "text", "Уровень\nпревышен");
      setValueLib("DIText", "foreCol", "{255,0,0}");
    }
    else{
      setValueLib("DIText", "text", "Уровень \nв норме");
      setValueLib("DIText", "foreCol", "{59,140,63}");
    }
  }


  public void updateStateText(mapping settings)
  {
		DebugN("updateStateText");
    tooltip.toolTipText(dpGetDescription(dpSubStr(settings["dpName"], DPSUB_DP)+ "."));
    dpConnect("updateStateTextCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateTextCB(string dpName, bool value)
  {
		DebugN("updateStateTextCB");
		DIText1.visible(value);
		DIText2.visible(!value);
  }


  public void updateStateFat(mapping settings)
  {
    dpConnect("updateStateFatCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateFatCB(string dpName, anytype value)
  {
    if(value)
    {
      setValueLib("DIText", "text", "Уровень жира\nпревышен");
      setValueLib("DIText", "foreCol", "{255,0,0}");
    }
    else{
      setValueLib("DIText", "text", "Уровень жира\nв норме");
      setValueLib("DIText", "foreCol", "{118,121,127}");
    }
  }

    public void updateStateSound(mapping settings)
  {
    dpConnect("updateStateSoundCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateSoundCB(string dpName, anytype value)
  {
    if(value)
    {
      setValueLib("sound1", "backCol", "{255, 0, 0}");
      setValueLib("sound2", "backCol", "{255, 0, 0}");
    }
    else{
      setValueLib("sound1", "backCol", "{183, 184, 187}");
      setValueLib("sound2", "backCol", "{183, 184, 187}");
    }
  }

  public void updateStateRoom(mapping settings)
  {
    dpConnect("updateStateRoomCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateRoomCB(string dpName, anytype value)
  {
    if(value)
    {
      setValueLib("ROOM", "foreCol", "red");
    }
    else{
      setValueLib("ROOM", "foreCol", "{118, 121, 127}");
    }
  }
};

class SCADTECH_DI_SBIS:skifcontent{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateCB(string dpName, anytype value)
  {
    if(value)
    {
      setValueLib("tag", "visible", true);
      setValueLib("tag2", "visible", true);
      setValueLib("back", "visible", true);
    }
    else{
      setValueLib("tag", "visible", false);
      setValueLib("tag2", "visible", false);
      setValueLib("back", "visible", false);
    }
  }

  public void updateStateMSG(mapping settings)
  {
    dpConnect("updateStateCBMSG", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateCBMSG(string dpName, anytype value)
  {
    if(value)
    {
      setValueLib("tag", "visible", true);
      setValueLib("back", "visible", true);
    }
    else{
      setValueLib("tag", "visible", false);
      setValueLib("back", "visible", false);
    }
  }
};


class SCADTECH_DI_GAS_20:skifcontent{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateCB(string dpName, anytype value)
  {
    if(value)
    {
      setValueLib("DIText", "foreCol", "yellow");
      setValueLib("DIText", "shadowEnabled", true);
    }
    else{
      setValueLib("DIText", "foreCol", "{183, 184, 187}");
            setValueLib("DIText", "shadowEnabled", false);
    }
  }
};

class SCADTECH_DI_GAS_50:skifcontent{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateCB(string dpName, anytype value)
  {
    if(value)
    {
      setValueLib("DIText", "foreCol", "red");
      setValueLib("DIText", "shadowEnabled", true);
    }
    else{
      setValueLib("DIText", "foreCol", "{183, 184, 187}");
            setValueLib("DIText", "shadowEnabled", false);
    }
  }
};


class SCADTECH_DI_GAS_TABLO:skifcontent{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State.TimP:_online.._value");
  }

  public static updateStateCB(string dpName, anytype value)
  {
    if(value)
    {
      setValueLib("tag", "foreCol", "red");
      setValueLib("back", "backCol", "white");
      setValueLib("ELLIPSE", "backCol", "{34,107,100}");
    }
    else{
      setValueLib("tag", "foreCol", "{118, 121, 127}");
      setValueLib("back", "backCol", "{239, 239, 239}");
      setValueLib("ELLIPSE", "backCol", "{210, 210, 210}");
    }
  }
};


class SCADTECH_ZD_DI:skifcontent{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".State.TimP:_online.._value", settings["dpName"] + ".Color.On:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
    if(value[1])
    {
        setValueLib("right", "backCol", "green");
        setValueLib("left", "backCol", "green");
    }
    else{
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
    }

    if(value[2] == 1){
        setValueLib("top", "backCol", "red");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
      }
    else{
      setValueLib("top", "backCol", "green");
    }
  }
};


class SCADTECH_ZD_DI_DEMO:skifcontent{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["System"]+ ":" + settings["dpName"][1] +".State.TimP:_online.._value", settings["System"]+ ":" + settings["dpName"][2] +".State.TimP:_online.._value", settings["dpName"][1] + ".Color.On:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
    if(value[1])
    {
        setValueLib("right", "backCol", "green");
        setValueLib("left", "backCol", "green");
    }

    if(value[2])
    {
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
    }
    if(value[1] && value[2] || !value[1] && !value[2])
    {
        setValueLib("right", "backCol", "{118,121,127}");
        setValueLib("left",  "backCol", "{118,121,127}");
    }

    if(value[3] == 1){
        setValueLib("top", "backCol", "red");
        setValueLib("right", "backCol", "yellow");
        setValueLib("left", "backCol", "yellow");
      }
    else{
      setValueLib("top", "backCol", "green");
    }
  }
};

class SCADTECH_AI:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".OIPVisualValue:_online.._value",
                               settings["dpName"] + ".OIPState:_online.._value");
        tag.text(UpdateName(settings["dpName"]));

  }

  public void updateStateFlow(mapping settings){
    dpConnect("updateStateFlowCB", settings["dpName"] + "OIPVisualValue:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
		string val;
		sprintf(val, "%.1f", value[1]);
  bool invalid = dpName + ":_online.._invalid";
  string HaveUnit = dpGetUnit(dpName[1]);

  if (HaveUnit == "") {
    setValueLib("unit", "text" , "???");
  } else {
    setValueLib("unit", "text", HaveUnit);
  }

  int bit_31 = getBit(value[2], 31);
  int bit_30 = getBit(value[2], 30);

  if(bit_31){
    setValueLib("value", "foreCol", "red");
  }
  else
  {
    if(bit_30)
      setValueLib("value", "foreCol", "yellow");
    else
      setValueLib("value", "foreCol", "normAI");
  }

//   switch(value[2]){
//     case 1: setValueLib("value", "foreCol", "yellow"); break;
//     case 2: setValue("value", "foreCol", "red"); break;
//     default: setValue("value", "foreCol", "normAI"); break;
//   }

  if (false){
      setValueLib("value", "text", "___");
      setValueLib("value", "foreCol", "black");
    } else {
    setValueLib("value", "text", val);
    }
  }

  public static updateStateFlowCB(string dpName, anytype value){
    string val;
  		sprintf(val, "%.1f", value[1]);
    bool invalid = dpName + ":_online.._invalid";
    string HaveUnit = dpGetUnit(dpName[1]);

    if (HaveUnit == "") {
      setValueLib("unit", "text" , "???");
    } else {
      setValueLib("unit", "text", HaveUnit);
    }
  }
};


class SCADTECH_AI_BLUE:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".OIPVisualValue:_online.._value",
                               settings["dpName"] + ".OIPState:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
		string val;
		sprintf(val, "%.1f", value[1]);
  bool invalid = dpName + ":_online.._invalid";
  string HaveUnit = dpGetUnit(dpName[1]);

  if (HaveUnit == "") {
    setValueLib("unit", "text" , "???");
  } else {
    setValueLib("unit", "text", HaveUnit);
  }


  setValueLib("value", "foreCol", "blue");

//   switch(value[2]){
//     case 1: setValue("value", "foreCol", "yellow"); break;
//     case 2: setValue("value", "foreCol", "red"); break;
//     default: setValue("value", "foreCol", "normAI"); break;
//   }

  if (false){
      setValueLib("value", "text", "___");
      setValueLib("value", "foreCol", "black");
    } else {
    setValueLib("value", "text", val);
    }
  }
};


class SCADTECH_VENT:skifcontent{
  public void updateState(mapping settings)
  {
		if(dynlen(settings["dpName"]) > 2){
      dpConnect("updateStateWithModeCB",
									settings["System"]+ ":" + settings["dpName"][1] +".State.TimP:_online.._value", //Работа
									settings["System"]+ ":" + settings["dpName"][2] +".State.TimP:_online.._value", //Авария
									settings["System"]+ ":" + settings["dpName"][3] +".State.TimP:_online.._value"	//Режим (А/Р)
									);
    }
    else if(dynlen(settings["dpName"]) > 1){
      dpConnect("updateStateCB", settings["dpName"][1] +".State.TimP:_online.._value", settings["System"]+ ":" + settings["dpName"][2] +".State.TimP:_online.._value");
    }
    else{
      dpConnect("updateStateOneCB", settings["dpName"] +".State.TimP:_online.._value");
    }

  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
		//Авария
    if(value[2]){
      setValueLib("state1", "backCol", "red");
      setValueLib("state2", "backCol", "red");
      setValueLib("ventFanblades1", "backCol", "black");
      setValueLib("ventFanblades2", "backCol", "_Transparent");
    }
    else{
			//В работе
      if(value[1]){
        setValueLib("state1", "backCol", "green");
        setValueLib("state2", "backCol", "green");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");


      }
			//Остановлен
      else{
        setValueLib("state1", "backCol", "yellow");
        setValueLib("state2", "backCol", "yellow");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
      }
 		}
  }

  public static updateStateOneCB(string dpName, anytype value)
  {
      if(value){
        setValueLib("state1", "backCol", "green");
        setValueLib("state2", "backCol", "green");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
        setValueLib("MODE_TEXT", "visible", "false");
      }
      else{
        setValueLib("state1", "backCol", "yellow");
        setValueLib("state2", "backCol", "yellow");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
                setValueLib("MODE_TEXT", "visible", "false");
      }

  }

	public static updateStateWithModeCB(dyn_string dpName, dyn_anytype value)
  {
		//Авария
    if(value[2]){
      setValueLib("state1", "backCol", "red");
      setValueLib("state2", "backCol", "red");
      setValueLib("ventFanblades1", "backCol", "black");
      setValueLib("ventFanblades2", "backCol", "_Transparent");
    }
    else{
			//В работе
      if(value[1]){
        setValueLib("state1", "backCol", "green");
        setValueLib("state2", "backCol", "green");
        setValueLib("ventFanblades1", "backCol", "blackDynTransparent");
        setValueLib("ventFanblades2", "backCol", "blackDynTransparentRev");
      }
			//Остановлен
      else{
        setValueLib("state1", "backCol", "yellow");
        setValueLib("state2", "backCol", "yellow");
        setValueLib("ventFanblades1", "backCol", "black");
        setValueLib("ventFanblades2", "backCol", "_Transparent");
      }
    }

		//Автоматический режим
		if (value[3]){
			setValueLib("MODE_TEXT", "text", "А");
			setValueLib("MODE_TEXT", "foreCol", "normAI");
		}
		//Ручной режим
		else{
			setValueLib("MODE_TEXT", "text", "P");
			setValueLib("MODE_TEXT", "foreCol", "blue");
		}
  }
};

public int setValueLib(string objShape, string objAttr, anytype value){
dyn_errClass err;
  try{
// shape olpenShape = getShape(myModuleName(), myPanelName(), this.name() + "." + objShape);
   shape olpenShape = getShapeStrict(objShape);
    if(shapeExists(olpenShape)){
      setValue(olpenShape,objAttr,value);
      return 1;
    }
    else{
      DebugN(this.name(),objShape);
    }
   return 0;
  }
  catch{
    err = getLastError();
    if (dynlen(err) > 0)
       return -1;
    return 0;
  }
}


class TAIRA_AI_Level:skifcontent
{
  public void updateState(mapping settings)
  {
    dpConnect("updateStateCB", settings["dpName"] + ".Value:_online.._value",
                               settings["dpName"] + ".state.emergLevel:_online.._value",
                               settings["dpName"] + ".state.warnLevel:_online.._value");
  }

  public static updateStateCB(dyn_string dpName, dyn_anytype value)
  {
		string val;
		sprintf(val, "%0d", value[1]);
    bool invalid = dpName + ":_online.._invalid";
    string HaveUnit = dpGetUnit(dpName[1]);

    int sizex, sizey, cur_level;
    getValue("lenght_bar", "size", sizex, sizey);

    if (value[1] > 100.0)
      value[1] = 100.0;
    else if (value[1] < 0)
      value[1] = 0;

    cur_level = (sizey * value[1]) / 100;
    setValueLib("level", "size", sizex, cur_level);

    if (HaveUnit == "") {
    setValueLib("unit", "text" , "???");
  } else {
    setValueLib("unit", "text", HaveUnit);
  }

    if (value[2])
    {
      setValueLib("value", "foreCol", "red");
      setValueLib("level", "backCol", "red");
    }
    else if (value[3])
    {
      setValueLib("value", "foreCol", "yellow");
      setValueLib("level", "backCol", "yellow");
    }
    else
    {
      setValueLib("value", "foreCol", "normAI");
      setValueLib("level", "backCol", "normAI");
    }

  if (false){
      setValueLib("value", "text", "___");
      setValueLib("value", "foreCol", "black");
    } else {
    setValueLib("value", "text", val);
    }
  }
};

// class SCADTECH_DI_SHUOD:skifcontent{
//
//   public void updateStateControl(mapping settings)
//   {
//     dpConnect("updateStateControlCB", settings["dpName"] + ".State.TimP:_online.._value");
//   }
//
//   public static void updateStateControlCB(string dpe, bool value)
//   {
//     if (value)
//     {
//       elementOn.visible(true);
//       elementOff.visible(false);
//     }
//     else
//     {
//       elementOn.visible(false);
//       elementOff.visible(true);
//     }
//   }
//
//
//   public void updateStateEmergUnblockAccess(mapping settings)
//   {
//     dpConnect("updateStateEmergUnblockAccessCB", settings["dpName"] + ".State.TimP:_online.._value");
//   }
//
//   public static void updateStateEmergUnblockAccessCB(string dpe, bool value)
//   {
//     if (value)
//     {
//       tag.color("SKIFAlarm");
//       elementOn.visible(true);
//       elementOff.visible(false);
//     }
//     else
//     {
//       tag.color("MnemoForePopUp");
//       elementOn.visible(false);
//       elementOff.visible(true);
//     }
//   }
//
//   public void updateStateRegime(mapping settings)
//   {
//     dpConnect("updateStateRegimeCB", settings["dpName"] + ".State.TimP:_online.._value");
//   }
//
//   public static void updateStateRegimeCB(string dpe, bool value)
//   {
//     if (value)
//     {
//       tag.color("SKIFAlarm");
//     }
//     else
//     {
//       tag.color("MnemoForePopUp");
//     }
//   }
//
//   public void updateStateUnblockAccess(mapping settings)
//   {
//     dpConnect("updateStateUnblockAccessCB", settings["dpName"] + ".State.TimP:_online.._value");
//   }
//
//   public static void updateStateUnblockAccessCB(string dpe, bool value)
//   {
//     if (value)
//     {
//       tag.color("SBISFontActive");
//       elementOn.visible(true);
//       elementOff.visible(false);
//     }
//     else
//     {
//       tag.color("MnemoForePopUp");
//       elementOn.visible(false);
//       elementOff.visible(true);
//     }
//   }
// };

int VentState(dyn_string dpName,dyn_anytype value){
    dyn_bool val;
    for(int i = 1; i <=dynlen(dpName); i++){
      string Temp = dpName[i];
      if(Temp.contains(".state.emergency")){
        val[1] = value[i];
      }
      if(Temp.contains(".state.starting")){
        val[2] = value[i];
      }
      if(Temp.contains("state.start")){
        val[3] = value[i];
      }
      if(Temp.contains("state.stoping")){
        val[4] = value[i];
      }
      if(Temp.contains("state.stop")){
        val[5] = value[i];
      }
    }

    if(val[1]){
      return 1;
    }
        else if(val[2]){
      return 2;
    }
             else if(val[3]){
           return 3;
    }
                 else if(val[4]){
               return 4;
    }
                     else if(val[5]){
                   return 5;
    }

    return 0;

}

//----------------------Static------------------------------
class TAIRA_ZD_Static:skifcontent
{
  public void update(mapping settings)
  {
    tag.text(UpdateName(settings["dpName"]));
    setValueLib("top", "backCol", "StaticObj");
    setValueLib("right", "backCol", "StaticObj");
    setValueLib("left", "backCol", "StaticObj");
    setValueLib("bottom", "backCol", "StaticObj");
  }

};

class TAIRA_DI_Static:skifcontent
{
  public void update(mapping settings)
  {
    tag.text(UpdateName(settings["dpName"]));
    setValueLib("state", "backCol", "StaticObj");
    setValueLib("tag", "foreCol", "black");
  }

  public void updateTerm(mapping settings)
  {
    setValueLib("tag", "foreCol", "StaticObj");
  }

};


class TAIRA_VENT_Static:skifcontent
{
  public void update(mapping settings){
    tag.text(UpdateName(settings["dpName"]));
    setValueLib("state1", "backCol", "StaticObj");
    setValueLib("state2", "backCol", "StaticObj");
    setValueLib("ventFanblades1", "backCol", "black");
    setValueLib("ventFanblades2", "backCol", "_Transparent");
  }

  public void updateSimp(mapping settings){
    tag.text(UpdateName(settings["dpName"]));
    setValueLib("state1", "backCol", "StaticObj");
  }

};


class TAIRA_AI_Static : skifcontent
{
    public void update(mapping settings)
    {

      setValueLib("warDiag", "visible", "false");
      tag.text(UpdateName(settings["dpName"]));
      setValue("tag", "foreCol", "StaticObj");
      setValue("value", "text", "___");
      setValue("value", "foreCol", "StaticObj");

      string HaveUnit = dpGetUnit(dpName + ".Value");
      setValue("unit", "foreCol", "StaticObj");
      if (HaveUnit == "") setValue("unit", "text", "");
      else setValue("unit", "text", HaveUnit);

    }

};


class TAIRA_VZZDR_Static:skifcontent
{
  public void update(mapping settings){
    tag.text(UpdateName(settings["dpName"]));
    setValueLib("vzzdState", "backCol", "StaticObj");
    setValueLib("open1", "visible", "true");
    setValueLib("open2", "visible", "true");
    setValueLib("open3", "visible", "true");
    setValueLib("close", "visible", "false");
  }
};

private global DI_scadtech PLC_DI;
private global SCADTECH_AI ST_AI;
private global SCADTECH_AI_BLUE ST_AI_BLUE;
private global SCADTECH_DI ST_DI;
private global SCADTECH_ZD_DI ST_ZD_DI;
private global SCADTECH_DI_SBIS ST_DI_SBIS;
// private global SCADTECH_DI_SHUOD ST_DI_SHUOD;
private global SCADTECH_DI_GAS_20 ST_DI_GAS_20;
private global SCADTECH_DI_GAS_50 ST_DI_GAS_50;
private global SCADTECH_DI_GAS_TABLO ST_DI_GAS_TABLO;
private global SCADTECH_VENT ST_VENT;
// private global AI_scadtech AI;
private global TAIRA_PP PP;
private global TAIRA_PUMP PUMP;
private global TAIRA_VENT VENT;
private global TAIRA_VENT_Double VENT_Double;
private global TAIRA_VENT_SYS VENT_SYS;
private global TAIRA_Electric_heater EH;
private global TAIRA_Electric_heater EH2;
private global TAIRA_Electric_heater_PNR EH_PNR;
private global TAIRA_ZD ZD;
private global TAIRA_VZZD VZZD;
private global TAIRA_VZZDR VZZDR;
private global TAIRA_DI DI;
private global TAIRA_AI AI;
private global TAIRA_AI_Level AI_Level;
private global TAIRA_VZZD_PV_Horiz VZZD_PV_Horiz;
private global SCADTECH_ZD_DI_DEMO ST_ZD_DI_DEMO;

//-------------Static------------------------
private global TAIRA_VENT_Static VENT_Static;
private global TAIRA_VZZDR_Static VZZD_Static;
private global TAIRA_DI_Static DI_Static;
private global TAIRA_ZD_Static ZD_Static;
private global TAIRA_AI_Static AI_Static;
 //-----------------------------------------


public const mapping mapClass = makeMapping(
 //-------------Static------------------------
 "TAIRA_ZD_Static", ZD_Static,
 "TAIRA_VENT_Static", VENT_Static,
 "TAIRA_DI_Static", DI_Static,
 "TAIRA_AI_Static", AI_Static,
 "TAIRA_VZZDR_Static", VZZD_Static,
 //-----------------------------------------

    "DI_scadtech", PLC_DI,
 "DI", DI,
 "SCADTECH_AI", ST_AI,
 "SCADTECH_AI_BLUE", ST_AI_BLUE,
 "SCADTECH_DI", ST_DI,
 "SCADTECH_ZD_DI", ST_ZD_DI,
 "SCADTECH_DI_SBIS", ST_DI_SBIS,
 "SCADTECH_DI_GAS_20", ST_DI_GAS_20,
 "SCADTECH_DI_GAS_50", ST_DI_GAS_50,
 "SCADTECH_DI_GAS_TABLO", ST_DI_GAS_TABLO,
 "SCADTECH_VENT", ST_VENT,
 "TAIRA_VZZD_PV_Horiz", VZZD_PV_Horiz,
//  "AI", AI,
 "TAIRA_PP", PP,
 "TAIRA_PUMP", PUMP,
 "TAIRA_VENT", VENT,
 "TAIRA_VENT_SYS", VENT_SYS,
 "TAIRA_VENT_Double", VENT_Double,
 "TAIRA_Electric_heater", EH,
 "TAIRA_Electric_heater_PNR", EH_PNR,
 "TAIRA_EH", EH2,
 "TAIRA_ZD", ZD,
 "TAIRA_VZZD", VZZD,
 "TAIRA_VZZDR", VZZDR,
 "TAIRA_DI", DI,
 "TAIRA_AI", AI,
 "TAIRA_AI_Level", AI_Level,
 "SCADTECH_ZD_DI_DEMO", ST_ZD_DI_DEMO
);
