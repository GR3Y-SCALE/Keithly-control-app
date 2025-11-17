----------------
-- TSP PROGRAM FOR PERFORMING TRANSFER SWEEPS
-- Sweeps over gate voltage and measures channel current

-- INPUT sweep start and end points with ABSOLUTE step size


-------- PARAMETERS --------
Vds = 0.1

VgStart = -60
VgEnd = 60
VgStep = 1

----- Device configuration -----
-- smua is gate 
-- smub is drain-source

-------- MAIN PROGRAM --------
reset()
display.clear()

-- Beep in excitement
beeper.beep(1, 600)

-- Clear buffers
smub.nvbuffer1.clear()
smua.nvbuffer1.clear()
-- Prepare buffers
smub.nvbuffer1.collectsourcevalues = 1
smua.nvbuffer1.collectsourcevalues = 1
format.data = format.ASCII
smub.nvbuffer1.appendmode = 1
smua.nvbuffer1.appendmode = 1
smub.measure.count = 1
smua.measure.count = 1

-- smub setup
smub.measure.delayfactor = 1.0
smub.measure.nplc = 10
smub.source.func = smub.OUTPUT_DCVOLTS
smub.sense = smub.SENSE_LOCAL
smub.source.autorangev = smub.AUTORANGE_ON
smub.source.limiti = 10e-5
smub.measure.rangei = 10e-5

-- smua setup
smua.measure.delayfactor = 1.0
smua.measure.nplc = 10
smua.source.func = smua.OUTPUT_DCVOLTS
smua.source.limiti = 10e-8

--DISPLAY settings
display.smub.measure.func = display.MEASURE_DCAMPS
display.smua.measure.func = display.MEASURE_DCAMPS
display.screen = display.smub_smua

-- MEASUREMENT ROUTINE

smub.source.levelv = Vds -- smub is fixed voltage
smub.source.output = smub.OUTPUT_ON

-- slow ramp to starting voltage
smua.source.levelv = 0
smua.source.output = smua.OUTPUT_ON
while I >= VgStart do
    I = I - 1
    smua.source.levelv = I
    delay(0.1)
end

Vg = VgStart
delay(3) -- wait for things to settle before starting the full sweep

-- Forward Vg scan
if VgStart < VgEnd then
    while Vg <= VgEnd do
        smua.source.levelv = Vg
        smua.source.output = smua.OUTPUT_ON
        delay(0.2)
        smub.measure.i(smub.nvbuffer1)
        smua.measure.i(smua.nvbuffer1)

        smua.source.output = smua.OUTPUT_OFF
        Vg = Vg + VgStep
    end

-- Reverse scan
elseif VgStart > VgEnd then
    while Vg >= VgEnd do
        smua.source.levelv = Vg
        smua.source.output = smua.OUTPUT_ON
        delay(0.2)
        smub.measure.i(smub.nvbuffer1)
        smua.measure.i(smua.nvbuffer1)

        smua.source.output = smua.OUTPUT_OFF
        Vg = Vg - VgStep
    end

else
    error("Invalid sweep parameters.")
end

smub.source.output = smub.OUTPUT_OFF
smua.source.output = smua.OUTPUT_OFF
waitcomplete()
-------- END --------
